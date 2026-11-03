# Диски, экран, сеть и снапшоты

## CD-ROM

У каждой машины есть привод CD-ROM (пустой, если `iso` не задан), поэтому
носитель можно менять на работающем госте:

```python
vm.storage.iso  # путь к вставленному ISO или None
vm.storage.eject()  # например, после установки ОС
vm.storage.insert("~/virtio-win.iso")
```

CD-ROM загружается первым; с пустым лотком прошивка переходит к диску, так
что после установки достаточно извлечь установочный образ.

## Диски

```python
vm.storage.disks()  # {"vda": "/.../vm.qcow2"}
target = vm.storage.attach(size="20G")  # новый qcow2 рядом с основным
vm.storage.attach("/data/scratch.img")  # готовый образ (raw для .img/.raw)
vm.storage.attach(size="5G", bus="sata", persist=False)
vm.storage.detach(target)  # образы, созданные attach(), удаляются
vm.storage.detach("vdc", remove_file=True)
vm.storage.stats()["vda"].written_bytes
```

KVM-машины используют чипсет q35, а сразу после определения резервируются
`pcie_ports` (по умолчанию 4) пустых PCIe root port, так что для живого
хотплага диска всегда есть свободный слот. Загрузочный диск отключить нельзя.

## Снапшоты (KVM)

```python
vm.snapshots.create("clean", description="чистая установка")
vm.snapshots.create()  # имя: snap-ГГГГммдд-ЧЧММСС
vm.snapshots.names()  # ["clean", ...]
"clean" in vm.snapshots, len(vm.snapshots)
vm.snapshots.revert("clean")
vm.snapshots.delete("clean")
```

Снапшот работающего qcow2-гостя включает его память. У Xen (libxl)
снапшотов нет — вызов бросит `UnsupportedOperationError`.

## Экран

```python
vm.display.uri  # "spice://127.0.0.1:5900" (или vnc://)
vm.display.graphics()  # все <graphics>: тип, адрес, порт
vm.display.screenshot("shot")  # bytes; сохраняется как shot.png / shot.ppm
viewer = vm.display.open_viewer()  # окно virt-viewer (subprocess.Popen)
vm.display.close_viewers()
```

Окна просмотрщика принадлежат объекту машины: `stop()`, `shutdown()`,
`close()` и `delete()` их закрывают.

Встроенная графика KVM настроена на чёткую и отзывчивую картинку: SPICE без
сжатия изображений, virtio-GPU (подстройка разрешения через `spice-vdagent`),
USB-планшет для абсолютного курсора, канал vdagent для общего буфера обмена и
два канала USB-перенаправления. Xen-гости получают VNC с VGA и USB-планшетом.
Поменять можно через `graphics="vnc"` или `graphics="none"` и `listen="0.0.0.0"`.

## Сеть

| `network=` | Смысл |
|---|---|
| `"auto"` (по умолчанию) | KVM session: `user`; KVM system: `network:default`; Xen: `bridge:xenbr0` |
| `"user"` | user-mode сеть QEMU, привилегии не нужны |
| `"default"` / `"network:ИМЯ"` | виртуальная сеть libvirt |
| `"bridge:br0"` | мост хоста |
| `"none"` | без сетевой карты |

```python
vm.network.interfaces()  # устройства на стороне хоста: ["vnet0"]
vm.network.addresses()  # {"enp1s0": ["192.168.122.40"]} (агент / DHCP / ARP)
vm.network.stats()["vnet0"].rx_bytes
```

`nic_model` выбирает карту (`virtio` на KVM; `e1000`, `rtl8139`, ...).
