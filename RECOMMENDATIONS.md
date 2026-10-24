# Repository Presentation Recommendations

These are safe, recommended improvements you can apply manually through the GitHub web UI
or by running the `gh` commands below once you're ready.

## Pinned repositories (GitHub profile → Customize your pins)

Recommended pin order:
1. `ai-driven-event-processing-system` — flagship technical project
2. `watchdog` (fork) — shows active upstream work on a real system
3. `RTOSPROJECT` — systems programming depth
4. `shopify-demo-with-aws-pipeline` — AWS serverless breadth
5. `kubeflow-spark` — cloud-native mini-project
6. `golangprac` — or `two-node-chat` if you prefer something more demonstrable

---

## Repository descriptions to update

Run these commands to update repo descriptions via the GitHub CLI:

```bash
gh repo edit soumadipcodeEnthusiast/RTOSPROJECT \
  --description "Preemptive and round-robin scheduling on FreeRTOS for constrained embedded systems"

gh repo edit soumadipcodeEnthusiast/agent-monitoring- \
  --description "Agent monitoring and observability tooling (Python)"

gh repo edit soumadipcodeEnthusiast/two-node-chat \
  --description "Real-time two-node chat over WebSockets (Node.js)"

gh repo edit soumadipcodeEnthusiast/golangprac \
  --description "Go language exercises and idiomatic patterns"

gh repo edit soumadipcodeEnthusiast/kubeflow-spark \
  --description "Kubeflow pipeline with Apache Spark for distributed data processing on Kubernetes"
```

---

## Topics to add

Topics improve discoverability. Suggestions per repo:

```bash
gh repo edit soumadipcodeEnthusiast/ai-driven-event-processing-system \
  --add-topic kafka,kubernetes,graphrag,temporal-fusion-transformer,anomaly-detection,aws,prometheus,grafana,spring-boot,python,terraform

gh repo edit soumadipcodeEnthusiast/RTOSPROJECT \
  --add-topic freertos,rtos,embedded-systems,c,scheduling,real-time

gh repo edit soumadipcodeEnthusiast/shopify-demo-with-aws-pipeline \
  --add-topic aws,lambda,step-functions,sqs,sns,serverless,event-driven

gh repo edit soumadipcodeEnthusiast/kubeflow-spark \
  --add-topic kubeflow,apache-spark,kubernetes,machine-learning,python
```

---

## ai-driven-event-processing-system README

The existing README is detailed and accurate. One suggested addition:
a **Quick Start** section at the top so contributors can run the system locally:

```bash
make up          # starts all services via Docker Compose
make produce     # generates sample events
make logs        # tail all services
```

This makes the project feel complete and approachable.

---

## Profile bio

Current: "devops and cloud learner"

Suggested (more specific, still honest):
"Building cloud-native systems · Contributing to CNCF and open-source infrastructure"

Update via: GitHub profile → Edit profile → Bio
