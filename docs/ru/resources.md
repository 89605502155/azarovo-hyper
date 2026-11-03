# Многопоточность и ресурсы

## Много машин, много потоков

```python
from concurrent.futures import ThreadPoolExecutor
from azarovo_hyper import hyper

h = hyper()
machines = [h.kvm(f"node{i}", memory="1G") for i in range(8)]
with ThreadPoolExecutor(8) as pool:
    list(pool.map(lambda vm: vm.start(), machines))
```

* **У каждой машины свой реентерабельный замок.** Операции над одной машиной
  идут по очереди (два `memory.set()` из разных потоков не перемешаются), над
  разными машинами — параллельно.
* **Одно соединение на URI** на все машины этого URI. Соединения libvirt
  потокобезопасны, а привязка отпускает GIL на время вызова, так что потоки
  действительно работают одновременно. Пул блокирует только свою служебную
  таблицу: медленное открытие соединения (например, к удалённому хосту) не
  задерживает другие URI.
* Ожидания (`start(wait=True)`, `shutdown()`, `wait_for()`) опрашивают
  состояние без глобальных замков, а `close()` из другого потока их прерывает.
* Счётчики загрузки CPU у каждой машины свои, а не общие.

Тесты это доказывают: медленный фейковый гипервизор (8 машин стартуют быстрее
половины последовательного времени), стресс-тесты жизненного цикла в 16
потоков на настоящем тестовом драйвере libvirt, пулы процессов
fork/forkserver/spawn и asyncio, а также параллельные настоящие KVM-гости.

## Процессы

Объекты машин можно передавать в `ProcessPoolExecutor` (с любым способом
запуска): они сериализуются по идентичности, и воркер получает новый объект,
привязанный к тому же гостю, со своим соединением.

```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor


def balloon(vm, size):
    return vm.memory.set(size)


machines = [h.kvm(f"node{i}").start() for i in range(4)]
ctx = mp.get_context("spawn")
with ProcessPoolExecutor(4, mp_context=ctx) as pool:
    print(list(pool.map(balloon, machines, ["1G", "1G", "2G", "2G"])))
```

fork тоже безопасен. В дочернем процессе каждое унаследованное соединение
бросается, но не закрывается и не переиспользуется (его деструктор отправил
бы «close» по сокету родителя), замки создаются заново, а удалить
`ephemeral`-машину может только создавший её процесс. Копии, полученные
сериализацией, никогда не бывают ephemeral.

## asyncio

Все вызовы блокирующие, но отпускают GIL, поэтому `asyncio.to_thread` даёт
настоящую параллельность и не блокирует цикл событий:

```python
import asyncio


async def main():
    machines = [h.kvm(f"node{i}") for i in range(8)]
    await asyncio.gather(*(asyncio.to_thread(vm.start) for vm in machines))
    samples = await asyncio.gather(*(asyncio.to_thread(vm.metrics) for vm in machines))
    await asyncio.gather(*(asyncio.to_thread(vm.delete) for vm in machines))


asyncio.run(main())
```

`loop.run_in_executor(process_pool, ...)` работает так же. Отмена задачи не
останавливает поток; чтобы прервать ожидающий `start()`, `shutdown()` или
`wait_for()`, вызовите `vm.close()`.

## Что и когда освобождается

| Событие | Освобождается |
|---|---|
| `stop()` / `shutdown()` | аренда соединения, окна просмотрщика, история загрузки CPU |
| чтение `vm.state` у выключенной машины | аренда, если машину сейчас не использует другой вызов |
| `close()`, выход из `with`, `del vm`, сборка мусора, выход интерпретатора | всё перечисленное; гость продолжает работать |
| то же с `ephemeral=True` | всё перечисленное **и** сам гость: выключается, определение удаляется, диски стираются |
| `delete()` | гость, его определение (с метаданными снапшотов, NVRAM, managed save), созданные библиотекой диски, затем `close()` |
| `Hyper.close()` / `with hyper() as h:` | `close()` у каждой созданной им машины |

Само соединение закрывается, как только на его URI не остаётся ни одной аренды:

```python
from azarovo_hyper import default_pool

kvm1 = hyper().kvm().start()
default_pool().active()  # {'qemu:///session': 1}
kvm1.stop()
default_pool().active()  # {}
```

Как это устроено:

* контроллеры машины (`vm.memory`, `vm.cpu`, ...) ссылаются только на сессию,
  а не на саму машину, поэтому `del kvm1` освобождает объект сразу, счётчиком
  ссылок, не дожидаясь сборщика циклов;
* очистка — это колбэк `weakref.finalize`: он выполняется ровно один раз — из
  `close()`, при сборке мусора или в `atexit`;
* неудачные операции откатываются: диск, созданный под домен, который libvirt
  отверг, или под неудавшийся хотплаг, удаляется обратно;
* обращение к закрытому объекту бросает `VMClosedError`, а не трогает
  устаревший дескриптор.
