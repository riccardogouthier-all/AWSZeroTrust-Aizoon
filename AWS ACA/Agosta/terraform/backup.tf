resource "aws_backup_vault" "lab" {
  name          = "${var.project}-backup"
  force_destroy = false
}

resource "aws_backup_plan" "lab" {
  name = "${var.project}-daily"
  rule {
    rule_name         = "daily-0200-utc"
    target_vault_name = aws_backup_vault.lab.name
    schedule          = "cron(0 2 * * ? *)"
    start_window      = 60
    completion_window = 180
    lifecycle {
      delete_after = 7
    }
  }
}

resource "aws_iam_role" "backup" {
  name = "${var.project}-backup"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "backup.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# Snapshot EC2: consistenza applicativa e ripristino devono essere provati nell'ambiente reale.
# Conservare i dati Docker su EBS, non su volumi esterni esclusi da questa selezione.
resource "aws_backup_selection" "hosts" {
  name         = "${var.project}-hosts"
  plan_id      = aws_backup_plan.lab.id
  iam_role_arn = aws_iam_role.backup.arn
  resources    = [for host in aws_instance.host : host.arn]
  depends_on   = [aws_iam_role_policy_attachment.backup]
}
