# Kasm Cua Container

Containerized virtual desktop for Computer-Using Agents (CUA). Utilizes Kasm's MIT-licensed Ubuntu XFCE container as a base.

## Usage

Building the container:

```bash
docker build -t kasm-cua .
```

Running the container:
```bash
docker run --rm -it --shm-size=512m -p 6901:6901 -p 8000:8000 -e VNC_PW=password kasm-cua
```
A VNC client will be available at `localhost:6901` with the username `kasm-user` and password `password`.

The container will run a Computer Server instance in the background. You can access the Computer Server API at `http://localhost:8000` or using the cua Computer SDK.

## Creating a snapshot

You can create a snapshot of the container at any time by running:
```bash
docker commit <container_id> kasm-cua-snapshot
```

You can then run the snapshot by running:
```bash
docker run --rm -it --shm-size=512m -p 6901:6901 -p 8000:8000 -e VNC_PW=password kasm-cua-snapshot
```
