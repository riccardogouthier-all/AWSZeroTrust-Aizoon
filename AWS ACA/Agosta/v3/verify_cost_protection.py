"""Read back the cost guard and simulate permissions without stopping any host."""
import json
from datetime import datetime, timezone
from decimal import Decimal
from ops import ROOT,SESSION,outputs,CONFIG,checked_account
account=SESSION.client('sts').get_caller_identity()['Account'];assert account==checked_account()
budgets=SESSION.client('budgets');budget=budgets.describe_budget(AccountId=account,BudgetName=f'{CONFIG.get("project", "aizoon-personal")}-cost-budget')['Budget'];actions=budgets.describe_budget_actions_for_budget(AccountId=account,BudgetName=budget['BudgetName'])['Actions']
assert Decimal(budget['BudgetLimit']['Amount'])==20 and budget['TimeUnit']=='MONTHLY'
assert not budget['CostTypes']['IncludeCredit'] and not budget['CostTypes']['IncludeRefund']
assert len(actions)==1
action=actions[0];assert action['ApprovalModel']=='AUTOMATIC' and action['Status']=='STANDBY' and action['NotificationType']=='ACTUAL'
assert action['ActionThreshold']=={'ActionThresholdValue':100.0,'ActionThresholdType':'PERCENTAGE'}
ids=sorted(v['id'] for v in outputs()['instances'].values());assert sorted(action['Definition']['SsmActionDefinition']['InstanceIds'])==ids
assert action['Definition']['SsmActionDefinition']['ActionSubType']=='STOP_EC2_INSTANCES'
iam=SESSION.client('iam');arns=[f'arn:aws:ec2:{SESSION.region_name}:'+account+':instance/'+i for i in ids];outside=f'arn:aws:ec2:{SESSION.region_name}:'+account+':instance/i-00000000000000000'
simulation=iam.simulate_principal_policy(PolicySourceArn=action['ExecutionRoleArn'],ActionNames=['ec2:StopInstances'],ResourceArns=arns+[outside],ContextEntries=[{'ContextKeyName':'aws:CalledVia','ContextKeyType':'stringList','ContextKeyValues':['ssm.amazonaws.com']}])['EvaluationResults']
for r in simulation:assert r['EvalDecision']==('allowed' if r['EvalResourceName'] in arns else 'implicitDeny'),r
runbook_arn=f'arn:aws:ssm:{SESSION.region_name}::automation-definition/AWS-StopEC2Instance:$DEFAULT'
ssm_sim=iam.simulate_principal_policy(PolicySourceArn=action['ExecutionRoleArn'],ActionNames=['ssm:StartAutomationExecution'],ResourceArns=[runbook_arn])['EvaluationResults'];assert ssm_sim[0]['EvalDecision']=='allowed'
plan=SESSION.client('freetier').get_account_plan_state();plan.pop('ResponseMetadata',None);assert plan['accountPlanType']=='FREE' and plan['accountPlanStatus']=='ACTIVE'
states={i['InstanceId']:i['State']['Name'] for reservation in SESSION.client('ec2').describe_instances(InstanceIds=ids)['Reservations'] for i in reservation['Instances']}
assert set(states.values())=={'running'}
policy=json.loads(SESSION.client('sns').get_topic_attributes(TopicArn=outputs()['alerts_topic'])['Attributes']['Policy']);assert any(x.get('Principal',{}).get('Service')=='budgets.amazonaws.com' for x in policy['Statement'])
result={'checked_at':datetime.now(timezone.utc).isoformat(),'budget':budget,'action':action,'permission_simulation':[{'resource':r['EvalResourceName'],'decision':r['EvalDecision']} for r in simulation],'ssm_runbook_permission':ssm_sim[0]['EvalDecision'],'plan':plan,'instance_states':states,'forced_stop_tested':False,'limits':['Billing updates are delayed; 20 USD is a trigger, not a hard cap.','Only the three Terraform-managed EC2 instances are stopped. NAT, storage, snapshots and logs still incur costs.','Free-plan automatic account closure protects against overage only while the account remains FREE.']}
(ROOT/'evidence/cost-protection-verification.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps({'monthly_threshold_usd':20,'action_status':action['Status'],'approval':action['ApprovalModel'],'targets':len(ids),'permissions_test':'PASS','account_plan':plan['accountPlanType'],'instance_states':states,'forced_stop_tested':False},indent=2))
