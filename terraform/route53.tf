# NOTE: DNS is now managed by Cloudflare (cloudflare/ Terraform state).
# These Route53 records become dormant after nameservers are updated at the registrar.
# They are kept here for reference and potential rollback.

# Custom Domain Name for API Gateway
resource "aws_apigatewayv2_domain_name" "www" {
  domain_name = "www.petergrecian.co.uk"

  domain_name_configuration {
    certificate_arn = var.acm_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

# API Mapping to Custom Domain
resource "aws_apigatewayv2_api_mapping" "www" {
  api_id      = aws_apigatewayv2_api.mywebsite.id
  domain_name = aws_apigatewayv2_domain_name.www.id
  stage       = aws_apigatewayv2_stage.default.id
}

# Route53 Record for Custom Domain
resource "aws_route53_record" "www" {
  zone_id = data.aws_route53_zone.pg.zone_id
  name    = "www.petergrecian.co.uk"
  type    = "CNAME"
  ttl     = 300
  records = [aws_apigatewayv2_domain_name.www.domain_name_configuration[0].target_domain_name]
}
