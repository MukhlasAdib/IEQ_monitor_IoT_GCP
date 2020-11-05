
--Create new table
USE ieq_data;
CREATE TABLE ieq_table (
    Number INT NOT NULL AUTO_INCREMENT,
    Temperature FLOAT,
    RH FLOAT,
    Illuminance FLOAT,
    CO2 FLOAT,
    SPL FLOAT,
    Date DATE,
    Time TIME,
    DeviceID VARCHAR(255), 
    GatewayID VARCHAR(255),
    PRIMARY KEY(Number)
);

--Insert test value
USE ieq_data;
INSERT INTO ieq_table (Temperature, RH, Illuminance, Date, Time, DeviceID, GatewayID)
VALUES (25.6,67,278,'2020-10-04','20:43:10','DEV000','GWY000');

--Delete all records
USE ieq_data;
DELETE FROM ieq_table;