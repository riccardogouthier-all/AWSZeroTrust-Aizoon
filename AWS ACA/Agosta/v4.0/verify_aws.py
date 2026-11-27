from datetime import datetime,timedelta,timezone
import json,socket,ssl,urllib.request,uuid
from ops import SESSION,ROOT,outputs,CONFIG,checked_account
account=checked_account();s=outputs(); result={}; now=datetime.now(timezone.utc)
def save(): (ROOT/'evidence'/'aws-verification.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
result['checked_at']=now
result['identity']=SESSION.client('sts').get_caller_identity()['Arn']
result['plan']=SESSION.client('freetier').get_account_plan_state()
result['plan'].pop('ResponseMetadata',None)
result['ssm_nodes']=[{'id':x['InstanceId'],'ping':x['PingStatus']} for x in SESSION.client('ssm').describe_instance_information()['InstanceInformationList']]
result['ec2']=[{'id':i['InstanceId'],'type':i['InstanceType'],'state':i['State']['Name'],'public_ip':i.get('PublicIpAddress'),'private_ip':i['PrivateIpAddress']} for res in SESSION.client('ec2').describe_instances(InstanceIds=[x['id'] for x in s['instances'].values()])['Reservations'] for i in res['Instances']]
result['public_ports']={}
for port in (443,22,3000,1514,1515,9200,55000):
 try:
  with socket.create_connection((s['waf_ip'],port),timeout=2):result['public_ports'][port]='reachable'
 except (OSError,TimeoutError):result['public_ports'][port]='not reachable'
logs=SESSION.client('logs');result['log_streams']=logs.describe_log_streams(logGroupName=f'/{CONFIG.get("project", "aizoon-personal")}/system')['logStreams']
cw=SESSION.client('cloudwatch');result['alarms']=[{'name':a['AlarmName'],'state':a['StateValue']} for a in cw.describe_alarms(AlarmNamePrefix=f'{CONFIG.get("project", "aizoon-personal")}-')['MetricAlarms']]
result['custom_metrics']={}
for role,node in s['instances'].items():
 for metric,dims in [('mem_used_percent',[{'Name':'InstanceId','Value':node['id']}]),('disk_used_percent',[{'Name':'InstanceId','Value':node['id']},{'Name':'path','Value':'/'},{'Name':'fstype','Value':'ext4'}])]:
  d=cw.get_metric_statistics(Namespace='AizoonLab',MetricName=metric,Dimensions=dims,StartTime=now-timedelta(minutes=25),EndTime=now,Period=60,Statistics=['Average'])['Datapoints'];result['custom_metrics'][role+'_'+metric]=len(d)
result['flow_objects']=len(SESSION.client('s3').list_objects_v2(Bucket=s['logs_bucket'],MaxKeys=50).get('Contents',[]))
context=ssl.create_default_context(cafile=str(ROOT/'lab-ca.crt'));base='https://'+s['waf_ip'];password=uuid.uuid4().hex+'Aa!9';email='qa-'+uuid.uuid4().hex+'@example.invalid'
def post(path,data):
 req=urllib.request.Request(base+path,json.dumps(data).encode(),{'Content-Type':'application/json'})
 with urllib.request.urlopen(req,context=context,timeout=30) as r:return r.status,json.load(r)
status,_=post('/api/Users/',{'email':email,'password':password,'passwordRepeat':password})
login,data=post('/rest/user/login',{'email':email,'password':password})
result['functional_api']={'registration':status,'login':login,'token_returned':bool(data.get('authentication',{}).get('token')),'synthetic_email':email}
assert status==201 and login==200 and result['functional_api']['token_returned']
# This tests alarm delivery explicitly; it does not simulate a real CPU incident.
cw.set_alarm_state(AlarmName=f'{CONFIG.get("project", "aizoon-personal")}-web-cpu',StateValue='ALARM',StateReason='Controlled synthetic delivery test')
sqs=SESSION.client('sqs');messages=sqs.receive_message(QueueUrl=s['alerts_queue_url'],MaxNumberOfMessages=10,WaitTimeSeconds=10).get('Messages',[])
result['alarm_delivery']={'synthetic':True,'received_messages':len(messages),'cpu_test_seen':any('Controlled synthetic delivery test' in m['Body'] for m in messages)}
for m in messages:sqs.delete_message(QueueUrl=s['alerts_queue_url'],ReceiptHandle=m['ReceiptHandle'])
cw.set_alarm_state(AlarmName=f'{CONFIG.get("project", "aizoon-personal")}-web-cpu',StateValue='OK',StateReason='Controlled test finished')
backup_file=ROOT/'evidence'/'backup-job.json'
if not backup_file.exists():
 job=SESSION.client('backup').start_backup_job(BackupVaultName=s['backup_vault'],ResourceArn=f'arn:aws:ec2:{SESSION.region_name}:{account}:instance/'+s['instances']['web']['id'],IamRoleArn=f'arn:aws:iam::{account}:role/{CONFIG.get("backup_role_name", "aizoon-personal-backup")}',Lifecycle={'DeleteAfterDays':1})
 job.pop('ResponseMetadata',None);backup_file.write_text(json.dumps(job,indent=2,default=str),encoding='utf-8')
result['backup']=SESSION.client('backup').describe_backup_job(BackupJobId=json.loads(backup_file.read_text())['BackupJobId']);result['backup'].pop('ResponseMetadata',None)
save();print(json.dumps(result,indent=2,default=str))
