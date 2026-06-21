# CloudOps Console cluster agent

Generate a short-lived pairing token in **Kubernetes → Connect cluster**, then install this chart. The agent makes outbound HTTPS/WebSocket connections only. It receives read-only investigation and vulnerability-scan jobs; the chart does not grant access to Kubernetes Secrets or mutation verbs.

```sh
helm upgrade --install cloudops-agent ./helm/cloudops-agent \
  --namespace cloudops-agent --create-namespace \
  --set-string controlPlaneUrl=https://your-console.example.com \
  --set-string pairingToken=coa_REPLACE_ME \
  --set-string clusterName=production
```

Use a published backend image containing `kubectl`, Trivy, and the Python application by overriding `image.repository` and `image.tag`.
