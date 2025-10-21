from src import calculation
from src import plot

#calculation.run_calculation()
plot.run_plotting(
    h5_path= 'results/7EWS_κ = 2.0_630720000.0years/sim_20years.h5', 
    x_range=(-150.0, 0.0), 
    y_range=(-50.0, 50.0)
    )
