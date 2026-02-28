import h5py
import numpy as np

class H5Writer:
    def __init__(self, path, n_EWS, compression="lzf", flush_every=365):
        self.h5 = h5py.File(path, "w")
        self.h5.attrs["format"] = "SubTerra_Simulation_Results"
        self.h5.attrs["version"] = "1.0"
        self.n_EWS = n_EWS
        self.i = 0
        self.flush_every = flush_every

        # 1D Zeitreihen
        self.ds = {}
        for name, dtype in [
            ("error_result", "f4"),
            ("E_probe_result", "f4"),
            ("E_flux_result", "f4"),
            ("Delta_E_result", "f4"),
            ("E_in_out", "f4"),
            ("Q_probe", "f4"),
            ("E_storage", "f4"),
            ("days", "i4"),
        ]:
            self.ds[name] = self.h5.create_dataset(
                f"timeseries/{name}",
                shape=(0,), maxshape=(None,),
                dtype=dtype, compression=compression, chunks=True
            )

        # 2D: pro-EWS (Spalten = Bohrungen)
        self.W_el = self.h5.create_dataset(
            "per_ews/W_el_values",
            shape=(0, n_EWS), maxshape=(None, n_EWS),
            dtype="f4", compression=compression, chunks=(1, n_EWS)
        )
        self.Temp_EWS = self.h5.create_dataset(
            "per_ews/Temp_EWS_values",
            shape=(0, n_EWS), maxshape=(None, n_EWS),
            dtype="f4", compression=compression, chunks=(1, n_EWS)
        )

        # Optional: Vertex-Snapshots (beliebige Shapes) als Gruppe
        self.snapshots = self.h5.create_group("snapshots")

    def add_vertex_snapshot_full(self, name, mesh, T, compression="lzf"):
            """
            Speichert das Feld in Vertex-Darstellung (DOLFINx):
            - coords: (num_vertices, gdim)
            - cells:  (num_cells, vertices_per_cell)
            - values: (num_dofs,)  (bei CG1 == num_vertices)
            Eignet sich perfekt für CG1 (lineare Lagrange).
            """
            g = self.snapshots.create_group(name)
            g.attrs["kind"] = "vertex"
            g.attrs["time_label"] = name  # z.B. "T_vertex_20.0a"

            # Geometrie
            coords = mesh.geometry.x                     # (Nverts, 3)
            gdim = mesh.geometry.dim
            coords_2d = coords[:, :gdim]                 # (Nverts, gdim)

            # Cells from topology connectivity
            mesh.topology.create_connectivity(mesh.topology.dim, 0)
            conn = mesh.topology.connectivity(mesh.topology.dim, 0)
            num_cells = mesh.topology.index_map(mesh.topology.dim).size_local
            cells = np.array(
                [conn.links(i) for i in range(num_cells)], dtype=np.int32
            )

            g.create_dataset("coords", data=coords_2d, compression=compression, chunks=True)
            g.create_dataset("cells",  data=cells,  compression=compression, chunks=True)

            # Feldwerte (CG1: DOF array == vertex values)
            vals = T.x.array                              # shape (Ndofs,)
            g.create_dataset("values", data=vals.astype("f4"), compression=compression, chunks=True)

            # Metadaten
            g.attrs["gdim"] = gdim
            g.attrs["num_vertices"] = coords_2d.shape[0]
            g.attrs["num_cells"] = cells.shape[0]

    def add_dof_snapshot(self, name, V_space, T, compression="lzf", save_mesh=None):
            """
            Speichert das Feld in DOF-Darstellung (DOLFINx, beliebiger Polynomialgrad):
            - dof_coords: (ndofs, gdim)
            - dof_values: (ndofs,)
            Optional: Mesh (coords+cells), falls gewünscht.
            """
            g = self.snapshots.create_group(name)
            g.attrs["kind"] = "dof"
            g.attrs["time_label"] = name

            # DOF-Koordinaten und Werte (DOLFINx)
            dof_coords_3d = V_space.tabulate_dof_coordinates()  # (ndofs, 3)
            gdim = V_space.mesh.geometry.dim
            dof_coords = dof_coords_3d[:, :gdim]
            dof_vals = T.x.array

            g.create_dataset("dof_coords", data=dof_coords, compression=compression, chunks=True)
            g.create_dataset("dof_values", data=dof_vals.astype("f4"), compression=compression, chunks=True)

            # Element/Space-Metadaten
            ufl_elem = V_space.ufl_element()
            g.attrs["family"] = str(ufl_elem.family())
            g.attrs["degree"] = int(ufl_elem.degree())
            g.attrs["gdim"]   = int(gdim)
            g.attrs["ndofs"]  = dof_coords.shape[0]

            if save_mesh is not None:
                mg = g.create_group("mesh")
                coords = save_mesh.geometry.x[:, :gdim]
                save_mesh.topology.create_connectivity(save_mesh.topology.dim, 0)
                conn = save_mesh.topology.connectivity(save_mesh.topology.dim, 0)
                num_cells = save_mesh.topology.index_map(save_mesh.topology.dim).size_local
                cells = np.array(
                    [conn.links(i) for i in range(num_cells)], dtype=np.int32
                )
                mg.create_dataset("coords", data=coords, compression=compression, chunks=True)
                mg.create_dataset("cells",  data=cells,  compression=compression, chunks=True)
                mg.attrs["gdim"] = int(gdim)

    def append_step(self, *, day, error, E_probe, E_flux, Delta_E, E_inout,
                    Q_probe=np.nan, E_storage=np.nan,
                    W_el_row=None, Temp_EWS_row=None):
        i = self.i
        self.i += 1

        # 1D resize
        for ds in self.ds.values():
            ds.resize((i+1,))
        # 2D resize
        self.W_el.resize((i+1, self.n_EWS))
        self.Temp_EWS.resize((i+1, self.n_EWS))

        # schreiben 1D
        self.ds["days"][i]          = int(day)
        self.ds["error_result"][i]  = float(error)
        self.ds["E_probe_result"][i]= float(E_probe)
        self.ds["E_flux_result"][i] = float(E_flux)
        self.ds["Delta_E_result"][i]= float(Delta_E)
        self.ds["E_in_out"][i]      = float(E_inout)
        self.ds["Q_probe"][i]       = float(Q_probe)
        self.ds["E_storage"][i]     = float(E_storage)

        # schreiben 2D
        if W_el_row is not None:
            self.W_el[i, :] = np.asarray(W_el_row, dtype=np.float32)
        if Temp_EWS_row is not None:
            self.Temp_EWS[i, :] = np.asarray(Temp_EWS_row, dtype=np.float32)

        if (i % self.flush_every) == 0:
            self.h5.flush()

    def add_vertex_snapshot(self, name: str, arr: np.ndarray):
        self.snapshots.create_dataset(name, data=np.asarray(arr), compression="lzf", chunks=True)

    def set_metadata(self, key: str, value):
         self.h5.attrs[key] = value

    def close(self):
        self.h5.flush()
        self.h5.close()