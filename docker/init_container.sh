docker build -t mabuhive:latest -f docker/Dockerfile .
docker run -p 8080:8000 --rm mabuhive:latest