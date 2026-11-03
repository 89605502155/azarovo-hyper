# Установка

## 1. Системные пакеты

Библиотека работает через libvirt, поэтому на хосте нужен сам гипервизор и
заголовки для сборки привязки `libvirt-python`.

Debian / Ubuntu:

```bash
sudo apt install -y qemu-kvm qemu-utils libvirt-daemon-system libvirt-clients \
                    pkg-config libvirt-dev python3-dev
sudo usermod -aG libvirt,kvm "$USER"    # затем перелогиниться
```

Fedora:

```bash
sudo dnf install -y @virtualization qemu-img pkgconf-pkg-config libvirt-devel python3-devel
```

Для Xen дополнительно нужны сам гипервизор Xen и `libvirt-daemon-driver-libxl`.

## 2. Библиотека

```bash
pip install "azarovo-hyper[libvirt]"
# или через uv
uv add "azarovo-hyper[libvirt]"
```

Extra `libvirt` ставит `libvirt-python`. Без него пакет всё равно
импортируется (удобно для тестов), а первое настоящее подключение бросит
`BackendUnavailableError` с подсказкой, что установить.

`virt-viewer` не обязателен — он нужен только для `vm.display.open_viewer()`.

## 3. Какой URI гипервизора используется

| Драйвер | URI по умолчанию | Как поменять |
|---|---|---|
| `kvm` | `qemu:///session` для обычного пользователя, `qemu:///system` для root | аргумент `uri=` или `AZAROVO_KVM_URI` |
| `xen` | `xen:///system` | аргумент `uri=` или `AZAROVO_XEN_URI` |

`qemu:///session` не требует ни root, ни членства в группах: гость работает
от вашего пользователя с user-mode сетью. `qemu:///system` даёт доступ к
сетям и мостам libvirt.

Удалённые хосты — так же: `uri="qemu+ssh://user@host/system"`.

## 4. Куда кладутся диски

Если не заданы `disk=` или `images_dir=`, образы создаются в

* `~/.local/share/azarovo-hyper/images` (или `$XDG_DATA_HOME/azarovo-hyper/images`);
* `/var/lib/libvirt/images`, если процесс запущен от root с системным URI.

## 5. Проверка

```python
from azarovo_hyper import hyper, libvirt_available

print(libvirt_available())  # True
print(hyper().host())  # HostInfo(uri='qemu:///session', cpus=..., ...)
```
