# FAQs

### Where are the VMs stored?

VMs are stored in `~/.lume`.

### How are images cached?

Images are cached in `~/.lume/cache`. When doing `lume pull <image>`, it will check if the image is already cached. If not, it will download the image and cache it, removing any older versions.

### Are VM disks taking up all the disk space?

No, macOS uses sparse files, which only allocate space as needed. For example, VM disks totaling 50 GB may only use 20 GB on disk.

### How do I get the latest macOS restore image URL?

```bash
lume ipsw
```

### How do I delete a VM?

```bash
lume delete <name>
```

### How do I install a custom linux image?

The process for creating a custom linux image differs than macOS, with IPSW restore files not being used. You need to create a linux VM first, then mount a setup image file to the VM for the first boot.

```bash
lume create <name> --os linux

lume run <name> --mount <path-to-setup-image> --start-vnc

lume run <name> --start-vnc
```
