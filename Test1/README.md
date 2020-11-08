# Codes for IoT Monitoring System Using GCP

*These codes are made based on Python 3.7*

*These codes have been tested for 24 hours operation*

*When we say 'device', it means a device that collect the data directly from sensors just like microprocessor. However, a gateway device like raspberry pi also can be used to collect data. In this case, the raspberry pi will also act as 'device'.*

*Instruction provided here are the steps required to run our codes. For details about how the codes work, you can check the comments written in each code.*

## Preparing the GCP Services

First of all, you need to prepare some services in GCP. For more details about each service configuration, we recommend you to read the documentation of the service.

### Cloud SQL

In our case, we use MySQL as our database and we will only use one table to store all of the data sent to GCP. In `sql_statements.sql`, we have listed several SQL queries that might be useful in for operating the database. As stated in the first query, the database (namely `ieq_data`) will contains a table (namely `ieq_table`) that will store these data: temperature, relative humidity, illuminance, CO2 concentration, noise level (SPL), date-time when the data was taken, the ID of the device that captured the data, and the ID of the gateway that sent the data to GCP. After you have initiated an instance in Cloud SQL, create a database (namely `ieq_data`) in than instance and then execute the first query in `sql_statements.sql`. To check whether the table has been created in the right way, you can execute `DEFINE ieq_table` to check the details of the table. Make sure it has all fields we mentioned before.

### Pub/Sub

Create a new topic in GCP Pub/Sub, don't check the CMEK option because we do not use it in this case as the authentification will be handled by IoT core. This topic will be used as the main topic for the telemetry data stream. 

### IoT Core

Create a new registry in GCP IoT Core. After that, create two new devices in the registry. We will use our own encryption keys for these devices. So first, you need to create two pairs of public-private RSA256 key, one for each device. After the keys have been created, upload the public key to the 'Authentication' menu in device setting. After the devices are ready, create a new gateway in IoT Core. Create one more RSA256 key pair and upload the public key to the 'Authentication' menu of the gateway. Set the 'Device authentification method' of the gateway to 'Both association and device credentials' as we assume that we want to use the most secure authentification method. 

### Cloud Function

We use Clound Function to move the data received by Pub/Sub to the SQL storage. Create a new function and set the trigger to the Pub/Sub topic that you have created before. Then, import two files in `cloud_function` folder to the function's source and set the entry point to `insert` function. Don't forget to fill the `connection_name` and `password` variables in the code with the ones that you own. You're ready to deploy the function.
