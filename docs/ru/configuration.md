# Конфигурация

Все параметры — именованные аргументы `hyper().kvm()` / `hyper().xen()` и
поля замороженного dataclass `VMSpec`. Параметры со значением `None`
получают значение по умолчанию драйвера из последних столбцов.

| Параметр | По умолчанию | Для KVM | Для Xen |
|---|---|---|---|
| `name` | `azarovo-<random>` | | |
| `title` | `""` | | |
| `iso` | `None` | | |
| `disk` | `<images_dir>/<name>.<format>` | | |
| `disk_size` | `"20G"` | | |
| `disk_format` | `"qcow2"` | | |
| `disk_preallocation` | `"falloc"` (см. [ресурсы](capacity.md)) | | |
| `disk_bus` | `None` | `virtio` | `xen` |
| `images_dir` | см. [установку](installation.md) | | |
| `memory`, `current_memory`, `min_memory`, `max_memory` | `2G`, `=memory`, `256M`, `8G` | | |
| `memory_slots`, `dimm_size` | `16`, `128M` | | |
| `balloon_period`, `balloon_autodeflate`, `free_page_reporting` | `1`, `False`, `False` | | |
| `memory_prealloc` | `False` | | |
| `resources` и его плоские параметры (`check_resources`, `memory_overcommit`, `cpu_overcommit`, `host_memory_reserve`, `host_disk_reserve`) | `ResourcePolicy()` | | |
| `vcpus`, `max_vcpus` | `2`, `max(vcpus, 8)` | | |
| `cpu_mode` | `"host-passthrough"` | | |
| `arch` | `"x86_64"` | | |
| `machine` | `None` | `q35` | `xenfv` |
| `firmware` | `"bios"` (`"efi"`) | | |
| `clock` | `"utc"` (`"localtime"` для Windows) | | |
| `network`, `nic_model` | `"auto"`, `None` | `virtio` | по умолчанию гипервизора |
| `graphics` | `None` | `spice` | `vnc` |
| `listen` | `"127.0.0.1"` | | |
| `video`, `video_heads` | `None`, `1` | `virtio` | `vga` |
| `usb_model` | `None` | `qemu-xhci` | |
| `pcie_ports` | `4` | | |
| `guest_agent` | `True` | | |
| `autostart`, `ephemeral` | `False`, `False` | | |
| `template` | `None` (встроенный) | `kvm.xml` | `xen.xml` |
| `extra_devices` | `()` | | |

```python
from azarovo_hyper import VMSpec, hyper

spec = VMSpec(name="bench", memory="4G", vcpus=4)
vm = hyper().kvm(spec=spec.with_(vcpus=6))
vm.spec  # спецификация с подставленными значениями драйвера
```

## Пресеты

`preset=` задаёт значения под конкретную гостевую ОС; явно переданные
параметры важнее.

| Пресет | Главное |
|---|---|
| `linux` | обычные значения по умолчанию |
| `ubuntu` | 4 ГиБ (2 ГиБ при загрузке), минимум 1,5 ГиБ, диск 25 ГиБ |
| `fedora` | 4 ГиБ (2148 МиБ при загрузке), минимум 1850 МиБ, диск 25 ГиБ |
| `debian` | 2 ГиБ, минимум 512 МиБ, диск 20 ГиБ |
| `alpine` | 512 МиБ, 1 vCPU, диск 4 ГиБ |
| `windows` | 4 ГиБ, SATA-диск 64 ГиБ, e1000e, QXL, UEFI, местное время |
| `reactos` | i686, i440fx, IDE, VGA/VNC, rtl8139, планшет на OHCI, местное время |
| `redox` | i440fx, IDE, VGA/VNC, e1000, xHCI |

```python
from azarovo_hyper import preset_names

preset_names()  # ['alpine', 'debian', 'fedora', 'linux', 'reactos', 'redox', 'ubuntu', 'windows']
```

## Встроенный XML

XML зашит в пакет (`azarovo_hyper/config/templates`): `kvm.xml`, `xen.xml` и
фрагменты устройств (`disk`, `cdrom`, `interface`, `spice`, `vnc`, `agent`,
`dimm`, `snapshot`). Каждый вариант рендеринга в тестах проверяется
RelaxNG-схемой самого libvirt. В домене KVM есть всё, что нужно адаптивному
регулятору:

* `<maxMemory slots>` + NUMA-ячейка — хотплаг DIMM;
* `<vcpu current=...>` ниже максимума — хотплаг vCPU;
* virtio-балун с `<stats period>` — живое изменение памяти и статистика гостя;
* запасные PCIe root port — хотплаг дисков;
* канал qemu-guest-agent — корректное выключение и IP-адреса;
* графический стек SPICE/virtio, описанный в разделе [устройства](devices.md).

## Свои шаблоны и устройства

```python
vm = hyper().kvm(extra_devices=("<watchdog model='i6300esb' action='reset'/>",))
vm = hyper().kvm(template="~/my-domain.xml")  # те же $-подстановки, что в kvm.xml
```

Значения XML-экранируются перед подстановкой, поэтому в путях и заголовках
можно использовать кавычки и `&`.

## Переменные окружения

| Переменная | Что делает |
|---|---|
| `AZAROVO_KVM_URI`, `AZAROVO_XEN_URI` | URI драйвера по умолчанию |
| `XDG_DATA_HOME` | база каталога образов по умолчанию |
