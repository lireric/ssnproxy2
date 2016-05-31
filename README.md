# ssnproxy2
Proxy for communication with SSN based devices (Python version)
Use MQTT messaging infrastructure

MQTT topics structure:

/ssn - root
/ssn/acc/<account_number> - account container
/ssn/acc/<account_number>/raw_data - unprocessed data from bus (rs485 etc)
/ssn/acc/<account_number>/obj/<object_number> - object container
/ssn/acc/<account_number>/obj/<object_number>/commands - commands to object
/ssn/acc/<account_number>/obj/<object_number>/events - events at object
/ssn/acc/<account_number>/obj/<object_number>/dev/<device_number> - device container
/ssn/acc/<account_number>/obj/<object_number>/dev/<device_number>/devicetime - timestamp of last value updating
/ssn/acc/<account_number>/obj/<object_number>/dev/<device_number>/<dev_channel>/in - set value
/ssn/acc/<account_number>/obj/<object_number>/dev/<device_number>/<dev_channel>/out - get value

/ssn/acc/<account_number>/telegram - telegram container (integration)
/ssn/acc/<account_number>/telegram/out - output messages
/ssn/acc/<account_number>/telegram/in  - input messages

/ssn/acc/<account_number>/sms - sms container (integration)
/ssn/acc/<account_number>/sms/out - output messages
/ssn/acc/<account_number>/sms/in  - input messages

/ssn/acc/<account_number>/email - email container (integration)
/ssn/acc/<account_number>/email/out - output messages
/ssn/acc/<account_number>/email/in  - input messages


Rename file ssnmqtt.cfg.sample to ssnmqtt.cfg and change preferences to you own.
