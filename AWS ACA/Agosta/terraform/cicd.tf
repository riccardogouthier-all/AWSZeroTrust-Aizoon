# Predisposizione CD, non una pipeline: il workflow GitHub Actions sarà aggiunto in seguito.
# Proteggere l'environment GitHub "lab" con revisione e limitazione del branch prima di abilitarlo.
# Il ruolo può eseguire comandi come root SOLO sulla VM web, non gestire Terraform o IAM.
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.github_repository != null && var.github_oidc_provider_arn == null ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "github_deploy" {
  count = var.github_repository != null ? 1 : 0
  name  = "${var.project}-github-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRoleWithWebIdentity"
      Principal = {
        Federated = var.github_oidc_provider_arn != null ? var.github_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
      }
      Condition = { StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:lab"
      } }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  count = var.github_repository != null ? 1 : 0
  role  = aws_iam_role.github_deploy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow", Action = "ssm:SendCommand"
        Resource = [
          "arn:aws:ssm:${var.region}::document/AWS-RunShellScript",
          aws_instance.host["web"].arn,
        ]
      },
      { Effect = "Allow", Action = "ssm:GetCommandInvocation", Resource = "*" },
    ]
  })
}
