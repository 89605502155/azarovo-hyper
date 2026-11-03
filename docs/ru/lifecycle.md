# Жизненный цикл

Каждый изменяющий метод возвращает саму машину, поэтому вызовы можно
сцеплять: `hyper().kvm().define().start().memory.set("1G")`.

| Метод | Что делает |
|---|---|
| `define()` | Создаёт диск (если его нет) и определяет домен; существующий домен с тем же именем подхватывает |
| `start(wait=True, timeout=60)` | При необходимости `define()`, затем включает; поставленного на паузу гостя возобновляет |
| `shutdown(timeout=120, force=True)` | Кнопка питания ACPI; через `timeout` — выключение «из розетки» (`force=False` вместо этого бросает `OperationTimeoutError`) |
| `stop()` | Мгновенное выключение, диск сохраняется |
| `restart(timeout=120)` | `shutdown()` + `start()` |
| `reboot()` / `reset()` | Перезагрузка силами гостя / аппаратный сброс (только работающий гость) |
| `suspend()` / `resume()` | Пауза и продолжение vCPU |
| `delete(remove_disk=None)` | Выключить, удалить определение (со снапшотами, NVRAM, managed save), удалить созданные библиотекой диски, закрыть объект |
| `close()` | Освободить всё, что держит объект; гость продолжает работать |
| `wait_for(*states, timeout=60)` | Ждать, пока машина не перейдёт в одно из состояний |

## Состояние

```python
from azarovo_hyper import VMState

vm.state  # VMState.RUNNING, SHUTOFF, PAUSED, ..., UNDEFINED
vm.is_running  # True / False
vm.exists  # определена ли на гипервизоре
vm.uuid, vm.xml  # UUID libvirt и живой XML домена
vm.autostart = True  # стартовать вместе с libvirtd
```

Номера `VMState` совпадают с `virDomainState` из libvirt.

## Чей диск

Библиотека запоминает (в metadata домена), создавала ли она диск, и
`delete()` удаляет его только в этом случае. `remove_disk=True` или `False`
задают выбор явно. Диски, подключённые через `vm.storage.attach()` без пути,
тоже считаются своими и удаляются в `delete()`.

## Подхват существующих машин

```python
vm = hyper().get("legacy-vm", hypervisor="kvm", uri="qemu:///system")
```

`get()` читает XML домена и сохраняет его размер памяти, потолок хотплага и
лимиты vCPU, так что контроллеры правильно ограничивают значения. Определение
машины с уже занятым именем (`hyper().kvm("legacy-vm").start()`) тоже
подхватывает её, а не переопределяет.

## Ошибки

Все исключения наследуются от `HyperError`:

| Исключение | Когда |
|---|---|
| `ConfigurationError` (ещё и `ValueError`) | неверный параметр, размер, пресет или аргумент |
| `VMStateError` | операция недопустима в текущем состоянии |
| `DomainNotFoundError` | машины или снапшота нет |
| `UnsupportedOperationError` | драйвер этого не умеет (например, снапшоты на Xen) |
| `OperationTimeoutError` (ещё и `TimeoutError`) | гость не пришёл в нужное состояние вовремя |
| `ConnectionFailedError` | гипервизор недоступен |
| `VMClosedError` | объект закрыт или удалён |
| `DiskError` | ошибка `qemu-img` |
| `BackendUnavailableError` | не установлен `libvirt-python` |
| `BackendError` | любая другая ошибка libvirt |
