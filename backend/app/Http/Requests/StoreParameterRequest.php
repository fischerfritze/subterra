<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StoreParameterRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true; // No auth for now
    }

    /**
     * Validation rules matching the parameter.json structure.
     * Every physical value is an object with {value, unit}.
     */
    public function rules(): array
    {
        return [
            // Top-level
            'meshMode'           => 'required|array|size:2',
            'meshMode.0'         => 'required|string|in:hexa,square',
            'meshMode.1'         => 'required|integer|min:1|max:10',
            'enableConvection'   => 'required|boolean',

            // Temperature references
            'temperatureAbsolute'       => 'required|array',
            'temperatureAbsolute.value' => 'required|numeric',
            'temperatureAbsolute.unit'  => 'required|string',
            'temperatureHot'            => 'required|array',
            'temperatureHot.value'      => 'required|numeric',
            'temperatureHot.unit'       => 'required|string',

            // Mesh
            'mesh'                       => 'required|array',
            'mesh.meshFactor.value'      => 'required|numeric|min:0.01',
            'mesh.meshFactor.unit'       => 'required|string',
            'mesh.meshFine.value'        => 'required|numeric|min:0.01',
            'mesh.meshFine.unit'         => 'required|string',
            'mesh.boreholeDistance.value' => 'required|numeric|min:0.1',
            'mesh.boreholeDistance.unit'  => 'required|string',
            'mesh.xLength.value'         => 'required|numeric|min:1',
            'mesh.xLength.unit'          => 'required|string',
            'mesh.yLength.value'         => 'required|numeric|min:1',
            'mesh.yLength.unit'          => 'required|string',
            'mesh.xCenter.value'         => 'required|numeric',
            'mesh.xCenter.unit'          => 'required|string',
            'mesh.yCenter.value'         => 'required|numeric',
            'mesh.yCenter.unit'          => 'required|string',

            // Time
            'time'                        => 'required|array',
            'time.timeStepHours.value'    => 'required|numeric|min:1',
            'time.timeStepHours.unit'     => 'required|string',
            'time.simulationYears.value'  => 'required|integer|min:1|max:100',
            'time.simulationYears.unit'   => 'required|string',

            // Ground
            'ground'                            => 'required|array',
            'ground.modelType.value'            => 'required|integer|in:1,2,3',
            'ground.modelType.unit'             => 'required|string',
            'ground.heatCapacityDensity.value'  => 'required|numeric|min:0',
            'ground.heatCapacityDensity.unit'   => 'required|string',
            'ground.thermalConductivity.value'  => 'required|numeric|min:0',
            'ground.thermalConductivity.unit'   => 'required|string',
            'ground.porosity.value'             => 'required|numeric|min:0|max:1',
            'ground.porosity.unit'              => 'required|string',
            'ground.temperature.value'          => 'required|numeric',
            'ground.temperature.unit'           => 'required|string',

            // Groundwater
            'groundwater'                            => 'required|array',
            'groundwater.density.value'              => 'required|numeric|min:0',
            'groundwater.density.unit'               => 'required|string',
            'groundwater.specificHeat.value'          => 'required|numeric|min:0',
            'groundwater.specificHeat.unit'           => 'required|string',
            'groundwater.thermalConductivity.value'   => 'required|numeric|min:0',
            'groundwater.thermalConductivity.unit'    => 'required|string',
            'groundwater.velocityX.value'             => 'required|numeric',
            'groundwater.velocityX.unit'              => 'required|string',
            'groundwater.velocityY.value'             => 'required|numeric',
            'groundwater.velocityY.unit'              => 'required|string',

            // Air
            'air'                            => 'required|array',
            'air.heatCapacityDensity.value'  => 'required|numeric|min:0',
            'air.heatCapacityDensity.unit'   => 'required|string',
            'air.thermalConductivity.value'  => 'required|numeric|min:0',
            'air.thermalConductivity.unit'   => 'required|string',

            // Power
            'power'                    => 'required|array',
            'power.coefficientA.value' => 'required|numeric',
            'power.coefficientA.unit'  => 'required|string',
            'power.coefficientB.value' => 'required|numeric',
            'power.coefficientB.unit'  => 'required|string',
            'power.pipeRadius.value'   => 'required|numeric|min:0.001',
            'power.pipeRadius.unit'    => 'required|string',
            'power.efficiency.value'   => 'required|numeric|min:0|max:1',
            'power.efficiency.unit'    => 'required|string',
        ];
    }

    /**
     * Build the complete parameter.json payload (adds version + useMode).
     */
    public function toParameterJson(): array
    {
        return array_merge(
            [
                'version' => '2',
                'useMode' => 'docker',
            ],
            $this->validated()
        );
    }
}
