# DomoticzWrapper

A documented wrapper around the Domoticz plugin API.

Install in `DomoticzWrapper` sub-folder of the Domoticz `plugins` folder:

```bash
cd ~
git clone https://github.com/gaelj/DomoticzWrapper.git domoticz/plugins/DomoticzWrapper
```

Usage (in `plugin.py`):

```python
from ..DomoticzWrapper.DomoticzWrapper import DomoticzWrapper as Domoticz, DomoticzDevice as D, DomoticzTypeName as TN, \
    DomoticzPluginParameter as PP, DomoticzDebugLevel as DL, DomoticzParameters as Parameters, DomoticzSettings as settings, \
    DomoticzDevices as Devices, DeviceParam, DomoticzImage as Image, DomoticzImages as Images
```
