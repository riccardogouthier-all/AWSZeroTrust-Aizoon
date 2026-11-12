"""Create dedicated S3 buckets using APIs allowed by the Learner Lab."""
import json
import re

from botocore.exceptions import ClientError
from ops import CONFIG, ROOT, SESSION


def ensure_bucket(s3, name, account, region, versioned=False):
    try:
        s3.head_bucket(Bucket=name, ExpectedBucketOwner=account)
    except ClientError as error:
        if error.response["Error"]["Code"] not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        request = {"Bucket": name}
        if region != "us-east-1":
            request["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**request)
    else:
        location = s3.get_bucket_location(Bucket=name, ExpectedBucketOwner=account).get("LocationConstraint") or "us-east-1"
        if location != region:
            raise RuntimeError(f"Bucket {name} belongs to region {location}; choose another project name")
    s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
    })
    s3.put_bucket_encryption(Bucket=name, ServerSideEncryptionConfiguration={
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}],
    })
    if versioned:
        s3.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": "Enabled"})


def main():
    if not CONFIG:
        raise RuntimeError("Copy terraform.tfvars.json.example to terraform/terraform.tfvars.json first")
    project, region = CONFIG["project"], CONFIG["region"]
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,24}", project):
        raise ValueError("Invalid project name")
    account = SESSION.client("sts").get_caller_identity()["Account"]
    record = {"account": account, "region": region, "project": project,
              "state_bucket": f"{project}-state-{account}", "logs_bucket": f"{project}-logs-{account}"}
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    file = evidence / "bootstrap.json"
    if file.exists() and json.loads(file.read_text()) != record:
        raise RuntimeError("Bootstrap targets changed; use a separate clone/runtime directory")
    file.write_text(json.dumps(record, indent=2))
    s3 = SESSION.client("s3")
    ensure_bucket(s3, record["state_bucket"], account, region, versioned=True)
    ensure_bucket(s3, record["logs_bucket"], account, region)
    backend = {"bucket": record["state_bucket"], "key": "lab/terraform.tfstate", "region": region,
               "encrypt": True, "use_lockfile": True}
    (ROOT / "terraform" / "backend.hcl").write_text("\n".join(f"{key} = {json.dumps(value)}" for key, value in backend.items()) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
