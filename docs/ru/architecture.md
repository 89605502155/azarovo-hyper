# Архитектура и расширение

Код следует принципам чистой архитектуры: зависимости направлены внутрь, и
про libvirt знают только адаптеры.

```
azarovo_hyper/
├── domain/     чистая модель: VMSpec, VMState, размеры, MemoryStats, запросы к XML
├── ports/      протоколы: Connection, Domain, DiskTool
├── adapters/   реализация на libvirt, пул соединений, qemu-img
├── config/     встроенные XML-шаблоны, пресеты, безопасный рендерер
├── drivers/    KvmDriver, XenDriver и реестр драйверов
├── vm/         VirtualMachine, её сессия и контроллеры
├── decorators.py
└── hyper.py    точка входа hyper()
```

* `domain` ничего не импортирует из других слоёв.
* `vm` работает только с протоколами из `ports`. Тесты подставляют в те же
  протоколы гипервизор в памяти.
* `drivers` превращают `VMSpec` в XML и выбирают стратегии (например, хотплаг
  DIMM на KVM и подъём потолка памяти на Xen).

## Декораторы

| Декоратор | Назначение |
|---|---|
| `@guarded` | замок машины + проверка «объект не закрыт» |
| `@synchronized`, `@alive` | две половины `@guarded` |
| `@chainable` | вернуть `self` для цепочек вызовов |
| `@requires_state(*states)`, `@requires_running` | предусловия по состоянию |
| `@requires_capability("snapshots")` | отказ, если драйвер этого не умеет |
| `@retry(times, delay, on)` | повтор нестабильных вызовов |
| `@decorate_public_methods(deco)` | декоратор класса, им переводятся ошибки libvirt |
| `@register_driver("name")` | добавить драйвер гипервизора |

## Новый гипервизор

```python
from azarovo_hyper import hyper, register_driver
from azarovo_hyper.drivers import Capabilities, KvmDriver


@register_driver("qemu")  # чистая эмуляция TCG, без KVM
class QemuDriver(KvmDriver):
    domain_type = "qemu"
    capabilities = Capabilities(snapshots=True, screenshot=True, dimm_hotplug=True)

    def builtin_uri(self) -> str:
        return "qemu:///session"


vm = hyper().qemu(memory="512M", cpu_mode="maximum").start()  # появился в hyper()
```

Драйвер с нуля наследует `HypervisorDriver`, реализует `builtin_uri`,
`auto_network`, `driver_values`, `cdrom_slot`, `plug_memory`,
`unplug_memory` и задаёт `template`, `capabilities` и `hardware`.

## Внутри системы управления

`hyper().get(name)` подключается к работающим гостям, `metrics()` даёт один
согласованный замер на такт, а контроллеры памяти и CPU применяют решения.
Раз у каждой машины свой замок, а соединения общие, поток мониторинга на
каждого гостя масштабируется без взаимных блокировок.

## Разработка

```bash
uv sync --locked                 # точные версии из uv.lock; нужны заголовки libvirt
uv run ruff check . && uv run ruff format --check .
uv run pytest                    # юнит-тесты + тесты на драйвере libvirt test:///
AZAROVO_LIVE=1 uv run pytest     # плюс настоящие KVM-гости (qemu:///session)
uv run pytest --cov
```
