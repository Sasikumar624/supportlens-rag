$proxyNames = @(
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "git_http_proxy",
    "git_https_proxy"
)

foreach ($name in $proxyNames) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($value -eq "http://127.0.0.1:9") {
        [Environment]::SetEnvironmentVariable($name, $null, "Process")
    }
}
