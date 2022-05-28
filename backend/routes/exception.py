from fastapi import APIRouter, status, Depends
from models.dbschema import  dbExceptionMessage, dbExceptionManager
from config.db import conn
from datetime import datetime, date
import pandas as pd
import janitor
from tabulate import tabulate
import json
from config.oauth2 import get_current_user
from config.redisdb import redis_client





exception = APIRouter(
    prefix = "/exceptions",
    tags=["exceptions"],
)

exceptionlist = []
materiallist = []

# Write a logic that returns a list of  exception ID  and exception message

# API call
# http://localhost:8000/exceptions/
@exception.get('/', status_code = status.HTTP_200_OK)
async def get_all_exception_info(user_id: int = Depends(get_current_user)):    
    return conn.execute(dbExceptionMessage.select()).fetchall()



@exception.get('/manager/{planner_id}',  status_code = status.HTTP_200_OK)
async def exception_manager(planner_id:str, start_date : str, end_date : str, user_id: int = Depends(get_current_user)):
    
    exception_manager_key = "exceptions" + "/" + "manager" + "/" + planner_id + "/" +  start_date + "--" + end_date
    
    redis_reponse = redis_client.get(exception_manager_key)
    
    # Check if the data exists in Cache
    if redis_reponse != None:
        print("Found the results in redis cache.......")
        return json.loads(redis_reponse)
    else: 
        print("I have not found the results in redis cache, computing now...")   

        sql_planner = """SELECT DISTINCT(material_9) from admin.MaterialMaster where planner = %s group by material_9"""
        df_list_manager = pd.DataFrame(conn.execute(sql_planner, planner_id).fetchall())
        list_manager = df_list_manager["material_9"].values.tolist()


        sql = """SELECT * FROM admin.Exception"""
        df_exception_manager = pd.DataFrame(conn.execute(sql).fetchall())
        
        if df_exception_manager.empty:
            
            response = {
            "planner" : planner_id,
            "start_date" : start_date,
            "end_date" : end_date,
            "result": json.loads(json.dumps(list(df_exception_manager.T.to_dict().values())))
        }
        
            return response
            
        dataframe_exception_manager = pd.concat([df_exception_manager["matnr"], df_exception_manager["cdate"], df_exception_manager["auskt"]], axis=1, keys=['matnr', 'cdate', 'auskt' ])

        dataframe_exception_manager = dataframe_exception_manager[dataframe_exception_manager['matnr'].isin(list_manager)]
        

        #  Data cleaning, replacing NaN with '0'
        dataframe_exception_manager['auskt'] = dataframe_exception_manager['auskt'].fillna(0)
        
        # Data filtering with respect to the start and end date
        dataframe_exception_manager_filtered = dataframe_exception_manager.filter_date('cdate', start_date, end_date)


        # Remove row that 'auskt' value has zero
        dataframe_exception_manager_filter = dataframe_exception_manager_filtered[dataframe_exception_manager_filtered['auskt'] > 0]

        # This would display all rows of a panda dataframe
        pd.set_option('display.max_rows', dataframe_exception_manager_filter.shape[0]+1)
        
        exception_manager_count = dataframe_exception_manager_filter.groupby('auskt').count()
        
        # count
        exception_manager_count.rename(columns = {'matnr':'count'}, inplace = True)
        exception_manager_count.drop('cdate', axis =1, inplace = True)
        
        # 'percentage'
        exception_manager_percentage = ((exception_manager_count['count'] / len(dataframe_exception_manager_filter))*100).to_frame()
        exception_manager_percentage.rename(columns = {'count':'percentage'}, inplace = True)

        # combine "count" and "percentage" column into one Table
        exception_manager_result = pd.concat([exception_manager_count, exception_manager_percentage], axis=1)

        # reset index
        exception_manager_result.reset_index(inplace=True)
        exception_manager = exception_manager_result.rename(columns = {'auskt':'exception'})
            
        
        # To find more details about exceptions
        
        local_exceptionMsg = []
        
        for item in list(exception_manager['exception']):
            sql = """SELECT * FROM admin.ExceptionMessage where exceptionID = %s"""
            exceptionMsg = conn.execute(sql, item).fetchall()
            df_exceptionMsg = pd.DataFrame(exceptionMsg, columns=["exceptionID", "exceptionMsg"])
            local_exceptionMsg = [
            df_exceptionMsg["exceptionID"][0],
                df_exceptionMsg["exceptionMsg"][0]
            ]
            exceptionlist.append(local_exceptionMsg)
            

        df_exceptionlist  = pd.DataFrame(exceptionlist, columns=["exceptionID", "exceptionMsg" ]) 
        
        exceptionlist.clear()
        
        response = {
            "planner" : planner_id,
            "start_date" : start_date,
            "end_date" : end_date,
            "result": json.loads(json.dumps(list(exception_manager.T.to_dict().values()))),
            "exceptions": json.loads(json.dumps(list(df_exceptionlist.T.to_dict().values())))    
        }
        
        redis_client.set(exception_manager_key, json.dumps(response) )
        return response
    
    


@exception.get('/matrix/{planner_id}/', status_code = status.HTTP_200_OK)
async def exception_matrix(planner_id:str, 
                                      start_date : str,
                                      end_date : str,
                    user_id: int = Depends(get_current_user)):
    
    # Reteriving materials
        
    exception_matrix_key = "exceptions" + "/" + "matrix" + "/" + planner_id + "/" +  start_date + "--" + end_date
    
    redis_reponse = redis_client.get(exception_matrix_key)
    
    # Check if the data exists in Cache
    if redis_reponse != None:
        print("Found the results in redis cache.......")
        return json.loads(redis_reponse)
    else: 
        print("I have not found the results in redis cache, computing now...")   
    
        sql_planner = """SELECT DISTINCT(material_9) from admin.MaterialMaster where planner = %s group by material_9"""
        df_list_manager = pd.DataFrame(conn.execute(sql_planner, planner_id).fetchall())
        list_manager = df_list_manager["material_9"].values.tolist()
        
        # Data Reading from MySQL 
        sql = """SELECT * FROM admin.Exception"""
        df_exception = pd.DataFrame(conn.execute(sql).fetchall()) 
        
        if df_exception.empty:
            response = {
            "planner" : planner_id,
            "start_date" : start_date,
            "end_date" : end_date,
            "result": json.loads(json.dumps(list(df_exception.T.to_dict().values())))
            }
        
            return response

        
        
        # 1 - matnr, 3 - cdate , 9 - auskt
        dataframe_exception = pd.concat([df_exception["matnr"], df_exception["cdate"], df_exception["auskt"]], axis=1)
        dataframe_exception = dataframe_exception[dataframe_exception["matnr"].isin(list_manager)]
        
    
        
        #  Data cleaning, replacing NaN with '0'
        dataframe_exception["auskt"] = dataframe_exception["auskt"].fillna(0)
        
        
        # Data filtering with respect to the start and end date
        dataframe_exception_filtered = dataframe_exception.filter_date("cdate", start_date=start_date, end_date=end_date)


        # Remove row that 'auskt' value has zero
        data_filter = dataframe_exception_filtered[dataframe_exception_filtered["auskt"] > 0]

        # This would display all rows of a panda dataframe
        pd.set_option('display.max_rows', data_filter.shape[0]+1)
        
        
        # "count" column
        exception_count = data_filter.groupby("matnr").count()
        exception_count.rename(columns = {"auskt":'count'}, inplace = True)
        exception_count.drop("cdate", axis =1, inplace = True)
        

        # 'percentage'
        exception_percentage = ((exception_count['count'] / len(data_filter))*100).to_frame()
        exception_percentage.rename(columns = {'count':'percentage'}, inplace = True)
        
        # combine "count" and "percentage" column into one Table
        result = pd.concat([exception_count, exception_percentage], axis=1)

        # reset index
        result.reset_index(inplace=True)
        exception_matrix = result.rename(columns = {1:'material'})
        
        
        # To find more details about the material
        
        local_material = []
        
        for item in list(exception_matrix["matnr"]):
            
            sql = """SELECT DISTINCT material, material_9, material_7, mat_description, mat_description_eng FROM admin.MaterialMaster where material_9 = %s"""
                
            df_material_master = pd.DataFrame(conn.execute(sql, item).fetchall(), columns=["material", "material_9" , "material_7", "mat_description", "mat_description_eng"])
                        
                
            local_material = [
                df_material_master["material"][0],
                df_material_master["material_9"][0],
                df_material_master["material_7"][0],
                df_material_master["mat_description"][0],
                df_material_master["mat_description_eng"][0],
            ]
            
            materiallist.append(local_material)
                
        df_materiallist = pd.DataFrame(materiallist,columns=["material", "material_9", "material_7", "mat_description", "mat_description_eng"] )
            
        materiallist.clear()
        
        response = {
            "planner" : planner_id,
            "start_date" : start_date,
            "end_date" : end_date,
            "result": json.loads(json.dumps(list(exception_matrix.T.to_dict().values()))) , 
            "materials" : json.loads(json.dumps(list(df_materiallist.T.to_dict().values()))),   
        }
        
        redis_client.set(exception_matrix_key, json.dumps(response) )
        return response
