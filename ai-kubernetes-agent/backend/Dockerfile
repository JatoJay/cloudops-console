FROM python:3.12-slim AS runtime

ARG KUBECTL_VERSION=v1.36.0
ARG TRIVY_VERSION=0.71.2
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y ca-certificates curl wget gnupg && \
    curl --fail --location --silent --show-error \
      --output /tmp/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" && \
    curl --fail --location --silent --show-error \
      --output /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl.sha256" && \
    echo "$(cat /tmp/kubectl.sha256)  /tmp/kubectl" | sha256sum --check && \
    install -o root -g root -m 0755 /tmp/kubectl /usr/local/bin/kubectl && \
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | \
      gpg --dearmor --output /usr/share/keyrings/trivy.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" \
      > /etc/apt/sources.list.d/trivy.list && \
    apt-get update && apt-get install --no-install-recommends -y "trivy=${TRIVY_VERSION}" && \
    rm -f /tmp/kubectl /tmp/kubectl.sha256 && \
    apt-get purge -y --auto-remove curl wget gnupg && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY --chmod=755 entrypoint.sh /app/entrypoint.sh

USER app
EXPOSE 8000

CMD ["/app/entrypoint.sh"]
