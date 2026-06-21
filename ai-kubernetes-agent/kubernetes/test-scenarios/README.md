# Kubernetes failure scenarios

These manifests create four intentional failures in the isolated `cloudops-test` namespace. Use only a disposable local cluster.

One local option is a dedicated Minikube profile:

```bash
minikube start --profile cloudops-e2e --driver=docker --cpus=2 --memory=3072
```

```bash
kubectl --context <local-context> apply -f kubernetes/test-scenarios/
kubectl --context <local-context> get pods -n cloudops-test -w
```

Wait for the states to settle, then select the same context in the dashboard and run an investigation. Expected evidence:

- `crashloop-missing-env`: `CrashLoopBackOff` plus a missing `DATABASE_URL` startup error.
- `invalid-image-tag`: `ImagePullBackOff`/`ErrImagePull` and a failed-pull event.
- `memory-limit`: `OOMKilled` after exceeding a 16 MiB limit.
- `selector-mismatch`: a service with no pods matching its selector.

Remove every fixture with one namespace deletion:

```bash
kubectl --context <local-context> delete namespace cloudops-test
```

Stop or delete the disposable profile when testing is complete:

```bash
minikube stop --profile cloudops-e2e
# Or remove it completely: minikube delete --profile cloudops-e2e
```
