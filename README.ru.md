# azarovo-hyper

[![CI](https://github.com/89605502155/azarovo-hyper/actions/workflows/ci.yml/badge.svg)](https://github.com/89605502155/azarovo-hyper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)

Высокоуровневый Python-API для создания, настройки и управления
виртуальными машинами **KVM** и **Xen** через libvirt: гость поднимается
одной строкой, а его атрибуты покрывают всё, что нужно адаптивной системе
управления гипервизором, — балунинг, горячее добавление памяти и vCPU,
хотплаг дисков, метрики, снапшоты, скриншоты.

[English documentation](README.md)

```python
from azarovo_hyper import hyper

kvm1 = hyper().kvm(iso="~/Загрузки/ubuntu.iso", preset="ubuntu").start()

kvm1.memory.set("3G")  # балун
kvm1.memory.plug("1G")  # хотплаг DIMM
kvm1.cpu.set(4)  # хотплаг vCPU
print(kvm1.metrics())  # CPU %, статистика балуна, дисковый ввод-вывод
kvm1.delete()  # нет ни домена, ни диска, ни соединения
```

## Возможности

* **Всё по умолчанию** — `hyper().kvm().start()` уже рабочая машина.
* **Встроенный XML, проверенный схемой libvirt**, для KVM (q35, NUMA-ячейка,
  слоты `maxMemory`, запасные PCIe-порты, virtio-балун со статистикой,
  гостевой агент, SPICE + virtio-GPU + USB-планшет + vdagent) и Xen HVM
  (libxl, VNC, xen-балун).
* **Память**: `set/grow/shrink` балуном в заданных границах, хотплаг DIMM на
  KVM, живой потолок памяти на Xen, статистика балуна изнутри гостя.
* **CPU**: живой хотплаг vCPU, замер загрузки отдельно для каждой машины.
* **Диски**: замена ISO на лету, хотплаг дисков, счётчики ввода-вывода.
* **Снапшоты, скриншоты, окна просмотра, IP-адреса, счётчики сетевых карт.**
* **Потокобезопасность by design**: замок на машину, одно общее соединение на
  URI; много гипервизоров и машин работают параллельно, не блокируя друг друга.
* **Детерминированная очистка**: `stop()` отдаёт соединение, `del vm` /
  `close()` / `with` освобождают всё, `ephemeral=True` ещё и удаляет гостя.
* Пресеты для Ubuntu, Fedora, Debian, Alpine, Windows, ReactOS и Redox.
* Чистая архитектура и подключаемые драйверы: `@register_driver("name")`.

## Установка

```bash
sudo apt install -y qemu-kvm qemu-utils libvirt-daemon-system pkg-config libvirt-dev python3-dev
pip install "azarovo-hyper[libvirt]"      # или: uv add "azarovo-hyper[libvirt]"
```

Обычный пользователь работает с `qemu:///session` (root не нужен), root — с
`qemu:///system`. Подробнее — [установка](docs/ru/installation.md).

## Использование

```python
from azarovo_hyper import VMState, hyper

h = hyper()
vm = h.kvm(
    "lab1",
    iso="~/isos/debian.iso",
    memory="4G",  # память при загрузке
    min_memory="1G",  # ниже memory.set() не опустится
    max_memory="16G",  # потолок хотплага
    vcpus=2,
    max_vcpus=8,
    network="auto",  # user-mode в session, сеть 'default' в system
)
vm.start()  # создаёт qcow2, определяет домен, включает

vm.state is VMState.RUNNING  # True
vm.display.uri  # 'spice://127.0.0.1:5900'
vm.display.open_viewer()  # окно virt-viewer, закроется вместе с ВМ

stats = vm.memory.stats()  # MemoryStats(actual_mib=..., usable_mib=..., rss_mib=...)
vm.memory.set(stats.actual_mib - 512)
vm.cpu.usage()  # загрузка с прошлого вызова, %

vm.storage.eject()  # после установки ОС
data = vm.storage.attach(size="50G")
vm.snapshots.create("installed")
vm.display.screenshot("screen.png")

vm.shutdown()  # ACPI, по таймауту — выключение
vm.delete()
```

Xen — так же: `hyper().xen("x1", iso=...).start()` на Xen-хосте.

Одноразовые машины:

```python
with hyper().kvm(memory="1G", ephemeral=True).start() as tmp:
    ...
# выключена, определение удалено, диск стёрт, соединение закрыто
```

Много машин параллельно:

```python
from concurrent.futures import ThreadPoolExecutor

machines = [h.kvm(f"node{i}") for i in range(8)]
with ThreadPoolExecutor(8) as pool:
    list(pool.map(lambda m: m.start(), machines))
```

## Документация

* [Обзор](docs/ru/index.md) · [Установка](docs/ru/installation.md) · [Быстрый старт](docs/ru/quickstart.md)
* [Жизненный цикл](docs/ru/lifecycle.md) · [Память и CPU](docs/ru/memory-cpu.md) · [Диски, экран, сеть](docs/ru/devices.md)
* [Конфигурация](docs/ru/configuration.md) · [Многопоточность и ресурсы](docs/ru/resources.md) · [Архитектура](docs/ru/architecture.md)

## Разработка

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest                    # юнит-тесты + драйвер libvirt test:///
AZAROVO_LIVE=1 uv run pytest     # плюс настоящие KVM-гости
```

## Лицензия

[MIT](LICENSE) © 2026 Andrey Ferubko
