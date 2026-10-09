# Applications: Stage 4

> 🚧 Planned. Not implemented yet.

This folder will contain the source code for application services:

- **rag-service**: a small Python RAG (retrieval-augmented generation) API using **Amazon Bedrock**, containerized and deployed to EKS with its own Helm chart

Each app will have its own `Dockerfile`, and its image will be built and pushed to **Amazon ECR** by the CI pipeline (Stage 3).