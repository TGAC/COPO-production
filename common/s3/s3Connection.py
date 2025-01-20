import boto3
from botocore.config import Config
from django.conf import settings as s
from django_tools.middlewares.ThreadLocal import get_current_request, get_current_user
from common.utils.helpers import notify_read_status
from common.utils.logger import Logger
from boto3.s3.transfer import TransferConfig
import logging
from common.dal.copo_da import EnaFileTransfer


class S3Connection():
    """
    Class to handle interations with ECS cloud storage via s3 service
    """

    def __init__(self, profile_id=str()):
        self.ecs_endpoint = s.ECS_ENDPOINT
        self.ecs_access_key_id = s.ECS_ACCESS_KEY_ID
        self.ecs_secret_key = s.ECS_SECRET_KEY

        self.expiration = 60 * 60 * 24
        self.path = '/'
        boto3.set_stream_logger(name='', level=logging.WARNING, format_string=None)
        self.s3_client = boto3.client('s3', endpoint_url=self.ecs_endpoint, verify=False,  
                                      config=Config(signature_version='s3v4', connect_timeout=120, read_timeout=240,
                                                    retries={"max_attempts": 10}, s3={'addressing_style': "path"}),
                                      aws_access_key_id=self.ecs_access_key_id,
                                      aws_secret_access_key=self.ecs_secret_key)
        # self.transport_params = {'client': self.s3_client}
        Logger().debug(
            msg=f"endpoint: {self.ecs_endpoint}, access key: {self.ecs_access_key_id}, secret: {self.ecs_secret_key}")

    def list_buckets(self):
        response = self.s3_client.list_buckets()
        Logger().debug(msg=response['Buckets'])
        return response["Buckets"]

    '''
    def list_objects(self, bucket):
        try:
            response = self.s3_client.list_objects(Bucket=bucket)
        except Exception as e:
            Logger().exception(e)
            return False
        try:
            contents = response["Contents"]
        except KeyError as e:
            # empty buckets have no 'Contents' fields
            return list()
        return contents
    '''

    def list_objects(self, bucket):
        return self._get_all_s3_objects(Bucket=bucket)

    def _get_all_s3_objects(self, **base_kwargs):
        continuation_token = None
        result = []
        while True:
            list_kwargs = dict(MaxKeys=1000, **base_kwargs)
            if continuation_token:
                list_kwargs['ContinuationToken'] = continuation_token

            try:    
                response = self.s3_client.list_objects_v2(**list_kwargs)
            except Exception as e:
                Logger().exception(e)
                return False
            try:
                contents = response["Contents"]
                result.extend(contents)
            except KeyError as e:
                # empty buckets have no 'Contents' fields
                return list()
            if not response.get('IsTruncated'):  # At the end of the list?
                return result
            continuation_token = response.get('NextContinuationToken')




    def get_object(self, bucket, key, loc):
        Logger().log("transfering file to: " + loc)
        KB = 1024
        MB = KB * KB
        config = TransferConfig(multipart_threshold=100 * MB, multipart_chunksize=64 * MB, io_chunksize=1 * MB,
                                max_concurrency=3, use_threads=True )
        #self.s3_client.download_file(bucket, key, loc, Config=config)
        with open(loc, 'wb') as data:
            self.s3_client.download_fileobj(Bucket=bucket, Key=key, Fileobj=data, Config=config)

        Logger().log("transfer complete: " + loc)

    def get_presigned_url(self, bucket, key, expires_seconds=24*60*60):
        '''
        Create a pre-signed url for uploading a single file to the s3 ECS
        :param bucket: name of the bucket to which the object sould be uploaded
        :param key: name of the file
        :param expires_seconds: how long until the url expires, default 24hrs
        :return:
        '''
        try:
            response = self.s3_client.generate_presigned_url('put_object', Params={'Bucket': bucket, 'Key': key},
                                                             ExpiresIn=expires_seconds)
            #response = response.replace("http://", "https://")
        except Exception as e:
            Logger().exception(e)
            response = e
        
        return response

    def check_for_s3_bucket(self, uid):
        '''
        Check for the existence of an s3 bucket
        :param uid: the name of the bucket
        :return: True if exists, False if not
        '''
        response = self.s3_client.list_buckets()
        bucket_list = response['Buckets']
        for bucket in bucket_list:
            if bucket["Name"] == uid:
                return True
        return False

    def make_s3_bucket(self, bucket_name):
        '''
        make an s3 bucks
        :param bucket_name: name of bucket to make
        :return: the bucket
        '''

        # try:
        return self.s3_client.create_bucket(Bucket=str(bucket_name))

        # except Exception as e:
        #    Logger().exception(e)
        #    response = "error"
        #    print(e)
        # return bucket

    def check_s3_bucket_for_files(self, bucket_name, file_list):
        '''
        Checks bucket_name for files supplied in file_list
        :param bucket_name: name of the s3 bucket to search
        :param file_list: list of files to look for
        :return: a list containing the names of files _not_ found
        '''
        try:
            try:
                profile_id = get_current_request().session["profile_id"]
            except AttributeError:
                profile_id = "xxxx"
            # channels_group_name = "read_status_" + profile_id

            missing_files = list()
            etags = dict()
            # get objects in the supplied bucket name
            bucket_files = self.list_objects(bucket=bucket_name)

            if not bucket_files:
                msg = "Bucket not found: " + bucket_name
                notify_read_status(data={"profile_id": profile_id}, msg=msg, action="info",
                                   html_id="sample_info")
                return False

            for f in file_list:

                # if found, iterate list of given files to see if each if present in the bucket
                files = f.split(",")
                for file in files:
                    found_flag = 0
                    print("Looking for", file)
                    file = file.strip()

                    notify_read_status(data={"profile_id": profile_id}, msg="Searching for: " + file, action="info",
                                       html_id="sample_info")
                    # time.sleep(2)
                    for bucket_file in bucket_files:

                        if file == bucket_file["Key"]:
                            print("Found", bucket_file["Key"])
                            found_flag = 1
                            etag = bucket_file["ETag"]
                            etag = etag.replace('"', '')
                            etags[file] = etag
                            break
                    if not found_flag:
                        # if a file is not found it should be recorded as such
                        missing_files.append(file)
            if len(missing_files) > 0:
                # report missing files
                notify_read_status(data={"profile_id": profile_id}, msg="Files Missing: " + str(
                    missing_files) + ". Please upload these files to COPO and try again.",
                                   action="error",
                                   html_id="sample_info")
                # return false to halt execution
                return False
            else:
                return etags

        except KeyError as e:
            notify_read_status(data={"profile_id": profile_id}, msg="Key Error occurred...cannot find key: " + str(e),
                               action="info",
                               html_id="sample_info")
            return False
        except Exception as e:
            Logger().exception(e)
            notify_read_status(data={"profile_id": profile_id}, msg="An error has occurred: " + str(e), action="info",
                               html_id="sample_info")
            raise e

    def validate_and_delete(self, target_id=str(), target_ids=list()):
        user = get_current_user()
        bucket_name = str(user.id) + "-" + user.username
        filestatus_map = EnaFileTransfer().get_transfer_status_by_ecs_path(ecs_locations=[ f"{bucket_name}/{key}" for key in target_ids])
        file_not_deleted = []
        status = False
        for key in target_ids:
            #ok to delete the file if there is no need to tranfer to ENA
            if filestatus_map.get(f"{bucket_name}/{key}", "ena_complete") == "ena_complete":
                self.s3_client.delete_object(Bucket=bucket_name, Key=key)
                status = True
            else:
                file_not_deleted.append(key)
                
        if status:
            return dict(status="success", message="File(s) have been deleted " +  ("excepts for following files in use: " + "<br/>".join(file_not_deleted) if file_not_deleted else "")  )
        else:
            return dict(status="failure", message="No File has been deleted and all selected file(s) in use")