from app.kubernetes.parsing import concise_error


def test_concise_error_removes_repeated_kubectl_discovery_noise() -> None:
    message = (
        'E0620 memcache.go:265] "Unhandled Error" connection refused\n'
        'E0620 memcache.go:265] "Unhandled Error" connection refused\n'
        "The connection to the server localhost:8080 was refused"
    )

    assert concise_error(message) == "The connection to the server localhost:8080 was refused"
