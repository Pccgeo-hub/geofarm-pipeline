$Env:CONDA_EXE = "D:/geofarm_epic1_starter/mamba\Scripts\conda.exe"
$Env:_CE_M = $null
$Env:_CE_CONDA = $null
$Env:_CONDA_ROOT = "D:/geofarm_epic1_starter/mamba"
$Env:_CONDA_EXE = "D:/geofarm_epic1_starter/mamba\Scripts\conda.exe"
$CondaModuleArgs = @{ChangePs1 = $True}
Import-Module "$Env:_CONDA_ROOT\shell\condabin\Conda.psm1" -ArgumentList $CondaModuleArgs

Remove-Variable CondaModuleArgs