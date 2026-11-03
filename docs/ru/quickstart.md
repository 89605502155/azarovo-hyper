# Быстрый старт

## Подготовить машину (один раз)

```bash
uv add azarovo-hyper
uv run azarovo-hyper setup     # Ubuntu; спросит пароль sudo
```

## Поднять машину

```python
from azarovo_hyper import hyper

kvm1 = (
    hyper()
    .kvm(
        "ubuntu-lab",
        iso="~/Загрузки/ubuntu-26.04-desktop-amd64.iso",
        preset="ubuntu",  # 4 ГиБ, диск 25 ГиБ, разумные границы балуна
    )
    .start()
)

print(kvm1)  # <VirtualMachine 'ubuntu-lab' kvm qemu:///session running>
print(kvm1.display.uri)  # spice://127.0.0.1:5900
kvm1.display.open_viewer()  # окно с установщиком
```

`hyper().kvm(...)` только собирает объект. `start()` создаёт qcow2-диск,
определяет домен из встроенного XML и включает его. У каждого параметра есть
значение по умолчанию, поэтому `hyper().kvm().start()` тоже работает.

## Работа с машиной

```python
kvm1.memory.set("3G")  # балуном ужать гостя до 3 ГиБ
kvm1.memory.plug("1G")  # горячо добавить планку DIMM на 1 ГиБ
kvm1.cpu.set(4)  # горячо добавить vCPU до 4
print(kvm1.metrics())  # CPU %, статистика балуна, счётчики дисков

kvm1.storage.eject()  # после установки — грузиться с диска
kvm1.snapshots.create("installed")
```

## Остановить и прибрать

```python
kvm1.shutdown()  # ACPI, через 120 с — выключение «из розетки»
kvm1.delete()  # убрать домен и созданный библиотекой диск
```

## Одноразовая машина

```python
with hyper().kvm(memory="1G", ephemeral=True).start() as tmp:
    tmp.memory.set("768M")
# здесь машины, её диска и соединения уже нет
```

## Несколько гипервизоров сразу

```python
h = hyper()
kvm1 = h.kvm("k1").start()
xen1 = h.xen("x1", iso="~/debian.iso").start()  # нужен Xen-хост
print(h.list("kvm"), h.host("kvm").free_mib)
```

## Подключиться к уже созданной машине

```python
vm = hyper().get("ubuntu-lab")  # сохраняет её собственные лимиты памяти и CPU
vm.start()
```
