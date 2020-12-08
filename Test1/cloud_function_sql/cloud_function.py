import sqlalchemy
import json
import base64
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
cfg = config['main']

connection_name = str(cfg['connection_name']) 
table_name = str(cfg['table_name'])
db_name = str(cfg['db_name'])
db_user = str(cfg['db_user'])
db_password = str(cfg['db_password'])

driver_name = 'mysql+pymysql'
query_string = dict({"unix_socket": "/cloudsql/{}".format(connection_name)})

def insert(event,context):
    if 'data' in event:
        jsonStr = base64.b64decode(event['data']).decode('utf-8')
        jsonDict = json.loads(jsonStr)
        fieldNames = ''
        fieldValues = ''

        if 'temp' in jsonDict:
            fieldNames = fieldNames + ',Temperature'
            fieldValues = fieldValues + ',' + str(jsonDict['temp'])
        if 'rh' in jsonDict:
            fieldNames = fieldNames + ',RH'
            fieldValues = fieldValues + ',' + str(jsonDict['rh'])
        if 'lux' in jsonDict:
            fieldNames = fieldNames + ',Illuminance'
            fieldValues = fieldValues + ',' + str(jsonDict['lux'])
        if 'co2' in jsonDict:
            fieldNames = fieldNames + ',CO2'
            fieldValues = fieldValues + ',' + str(jsonDict['co2'])
        if 'spl' in jsonDict:
            fieldNames = fieldNames + ',SPL'
            fieldValues = fieldValues + ',' + str(jsonDict['spl'])
        
        fieldNames = fieldNames + ',Datetime'
        fieldValues = fieldValues + ',\'' + str(jsonDict['date']) + ' ' + str(jsonDict['time']) + '\''

        fieldNames = fieldNames + ',DeviceID'
        fieldValues = fieldValues + ',\'' + str(jsonDict['devID']) + '\''
        fieldNames = fieldNames + ',GatewayID'
        fieldValues = fieldValues + ',\'' + str(jsonDict['gwyID']) + '\''

        fieldNames = fieldNames[1:] ; fieldValues = fieldValues[1:]

        insert_query = f'INSERT INTO {table_name} ({fieldNames}) VALUES ({fieldValues});'
        stmt = sqlalchemy.text(insert_query)
        
        db = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL(
            drivername=driver_name,
            username=db_user,
            password=db_password,
            database=db_name,
            query=query_string,
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800
        )
        try:
            with db.connect() as conn:
                conn.execute(stmt)
        except Exception as e:
            return 'Error: {}'.format(str(e))
        return 'ok'