# Highway Traffic Control System (HTCS) Vehicle

This C project represents a simulated vehicle on a highway.

It communicates with an MQTT broker in a way that
it publishes its position, speed, etc.
and subscribes to commands from a controller
in order to safely navigate through the traffic.

## Linux install

1. [Download Eclipse Paho MQTT C](https://www.eclipse.org/downloads/download.php?file=/paho/1.4/Eclipse-Paho-MQTT-C-1.3.1-Linux.tar.gz&mirror_id=1099)
2. Extract it in your ${HOME} folder
3. `cd path/to/repo/htcs-vehicle`
4. Run build.sh

## Windows install

1. [Download Eclipse Paho MQTT C](https://www.eclipse.org/downloads/download.php?file=/paho/1.4/eclipse-paho-mqtt-c-win32-1.3.1.zip)
2. Unzip under %USERPROFILE%\eclipse-paho-mqtt-c-win32-1.3.1\
3. Add %USERPROFILE%\eclipse-paho-mqtt-c-win32-1.3.1\lib to PATH
4. Open the Project with Visual Studio
5. Run with Debug x86

## Usage

Example Linux invocation for [MaQiaTTo](https://maqiatto.com) connection:
```shell script
htcs-vehicle \
--address maqiatto.com \
--username krisz.kern@gmail.com \
--password ***** \
--clientId 1 \
--topic krisz.kern@gmail.com/vehicles \
--preferredSpeed 120.0 \
--maxSpeed 210.0 \
--acceleration 7.3 \
--brakingPower 4.5 \
--size 3.4
```

With Visual Studio on Windows you can set the
command line arguments in the Debugger section of the Project properties.

You may have to set the target platform and windows sdk in the project properties, or clicking "retarget-project" in the right-click menu of the project in solution explorer.

The program requires the following command line arguments to function properly:

* address
    * the address of the MQTT broker
    * format: `[protocol://]hostname[:port]`
* username
    * the username for the MQTT broker
* password
    * the password for the MQTT broker
* clientId
    * arbitrary string
    * identifies the vehicle
* topic
    * the topic base of vehicles
* preferredSpeed
    * positive double
    * the preferred travel speed
    * unit: kilometres per hour
* maxSpeed
    * positive double
    * the maximum speed of the vehicle
    * unit: kilometres per hour
* acceleration
    * positive double
    * the constant acceleration of the vehicle
    * unit: the time it takes in seconds for the vehicle to reach 100 km/h from 0 km/h
* brakingPower
    * positive double
    * the constant braking power of the vehicle,
    * unit: the time it takes in seconds for the vehicle to reach 0 km/h from 100 km/h
* size
    * positive double
    * the length of the vehicle
    * unit: meter

At the start of the program, the vehicle will automatically subscribe to the topic:
`<topic base>/<client id>/command`  
It will receive commands from the controller on this topic.

After the subscription, the vehicle joins the highway traffic,
i.e. the vehicle publishes once to the topic:
`<topic base>/<client id>/join`  
It will send its constant parameters with this message:
* preferred speed
* maximum speed
* acceleration
* braking power
* size

After joining, the vehicle starts to move forward with the following default values:
* speed: 50 km/h
* distance taken: 0 meter
* in the merge lane
* maintaining speed

The vehicle periodically - each second - publishes its state information to the topic:
`<topic base>/<client id>/state`  
The following variables are sent with this message:
* lane
* distanceTaken
* speed
* accelerationState