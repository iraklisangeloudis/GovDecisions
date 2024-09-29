provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_artifact_registry_repository" "flask_repo" {
  location      = var.region
  repository_id = "flask-docker-repo"
  description   = "Docker repository for Flask app"
  format        = "DOCKER"
}

resource "google_cloud_run_service" "flask_service" {
  name     = "flask-app"
  location = var.region

  template {
    spec {
      containers {
        image = "us-central1-docker.pkg.dev/${var.project_id}/flask-docker-repo/flask-app:v1"
        env {
          name  = "FLASK_ENV"
          value = "production"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "all_users_run_invoker" {
  service = google_cloud_run_service.flask_service.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}
