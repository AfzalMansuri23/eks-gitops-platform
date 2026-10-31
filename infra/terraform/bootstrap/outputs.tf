output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "ecr_chart_repository_url" {
  value = aws_ecr_repository.chart.repository_url
}

output "github_plan_role_arn" {
  value = aws_iam_role.github_plan.arn
}

output "ecr_assistant_repository_url" {
  value = aws_ecr_repository.assistant.repository_url
}
