# Установка

> **Платформа.** azarovo-hyper проверена и рассчитана на **Linux, а именно
> Ubuntu** (22.04, 24.04, 26.04). Поддержка других дистрибутивов и
> операционных систем планируется в следующих версиях.

## Две команды

```bash
uv add azarovo-hyper              # или: pip install azarovo-hyper
uv run azarovo-hyper setup        # один раз на машину; спросит пароль sudo
```

1. `uv add` ставит библиотеку. У неё **нет зависимостей**, и ничего не
   компилируется: встроенный бэкенд обращается к системной `libvirt.so.0`
   напрямую через `ctypes`, поэтому не нужны ни `libvirt-dev`, ни
   `pkg-config`, ни `python3-dev`, ни компилятор C.
2. `azarovo-hyper setup` ставит сам гипервизор — `qemu-system-x86`,
   `qemu-utils`, `libvirt-daemon-system`, `libvirt-clients`, `ovmf` и
   `virt-viewer`, — включает libvirtd и добавляет вас в группы `libvirt` и
   `kvm`. Сначала печатает все команды и спрашивает подтверждение;
   `--dry-run` только печатает, `--yes` не спрашивает, `--no-viewer` не ставит
   `virt-viewer`. После этого один раз перелогиньтесь, чтобы группы применились.

Системные пакеты нельзя поставить самим `uv add`: Python-пакетам запрещено
запускать `sudo` во время установки, поэтому этот шаг — отдельная явная команда.

## Проверка машины

```bash
uv run azarovo-hyper doctor
```

```
[ok  ] operating system     Ubuntu 26.04.1 LTS
[ok  ] CPU virtualization   Intel VT-x
[ok  ] /dev/kvm             read/write
[ok  ] qemu:///session      connected (QEMU)
ready to run guests
```

Для каждой неудачной строки написано, что сделать. Работает и
`python -m azarovo_hyper doctor`.

## Бэкенды libvirt

| `AZAROVO_LIBVIRT_BACKEND` | Бэкенд | Установка |
|---|---|---|
| `native` (по умолчанию) | ctypes поверх `libvirt.so.0` | ничего дополнительно |
| `python` | официальный `libvirt-python` | `uv add "azarovo-hyper[libvirt]"` (компилируется, нужен `libvirt-dev`) |

API у обоих одинаковый, тесты гоняются на обоих.

## Какой URI гипервизора используется

| Драйвер | URI по умолчанию | Как поменять |
|---|---|---|
| `kvm` | `qemu:///session` для обычного пользователя, `qemu:///system` для root | аргумент `uri=` или `AZAROVO_KVM_URI` |
| `xen` | `xen:///system` | аргумент `uri=` или `AZAROVO_XEN_URI` |

`qemu:///session` не требует root: гость работает от вашего пользователя с
user-mode сетью. `qemu:///system` даёт доступ к сетям и мостам libvirt.
Удалённые хосты: `uri="qemu+ssh://user@host/system"`.

## Куда кладутся диски

Если не заданы `disk=` или `images_dir=`, образы создаются в
`~/.local/share/azarovo-hyper/images` (или `$XDG_DATA_HOME/azarovo-hyper/images`),
а при запуске от root с системным URI — в `/var/lib/libvirt/images`.

## Воспроизводимая среда разработки

```bash
git clone https://github.com/89605502155/azarovo-hyper && cd azarovo-hyper
uv sync --locked                 # точные версии из закоммиченного uv.lock
```
