# Память и CPU

Размеры принимаются целым числом МиБ (`2048`) или строкой (`"2G"`, `"512M"`,
`"1.5GiB"`). Результаты возвращаются в МиБ.

## Параметры памяти

| Параметр | Смысл | По умолчанию |
|---|---|---|
| `memory` | память при загрузке, она же исходный потолок балуна | `"2G"` |
| `current_memory` | размер балуна при загрузке | = `memory` |
| `min_memory` | ниже этого `memory.set()` никогда не опустится | `"256M"` |
| `max_memory` | потолок хотплага (`<maxMemory>` на KVM) | `"8G"` |
| `memory_slots` | слоты DIMM для хотплага (KVM) | `16` |
| `dimm_size` | размер одного `memory.plug()` по умолчанию | `"128M"` |
| `balloon_period` | период статистики балуна, с | `1` |

## Балунинг

```python
vm.memory.set("1536M")  # ограничивается [min_memory, maximum_mib]
vm.memory.grow("256M")  # текущее + 256 МиБ
vm.memory.shrink("256M")
vm.memory.set("2G", persist=True)  # записать и в конфигурацию

vm.memory.current_mib  # размер балуна сейчас
vm.memory.maximum_mib  # память при загрузке + горячо добавленная
vm.memory.set_stats_period(5)  # обновлять статистику гостя раз в 5 с
```

`stats()` возвращает `MemoryStats`:

```python
s = vm.memory.stats()
s.actual_mib  # размер балуна
s.usable_mib  # MemAvailable внутри гостя (нужен драйвер virtio-balloon)
s.unused_mib  # MemFree внутри гостя
s.rss_mib  # сколько гость занимает на хосте
s.free_mib  # usable -> unused -> actual - rss, что известно
s.used_mib, s.usage_percent
s.guest_reports  # False, пока драйвер в госте не прислал статистику
s.raw  # все поля, которые вернул libvirt
```

`balloon_autodeflate=True` позволяет гостю сдуть балун при OOM;
`free_page_reporting=True` возвращает освобождённые страницы хосту. Оба
выключены по умолчанию, чтобы измерения были воспроизводимыми.

## Горячее добавление памяти

```python
vm.memory.plug()  # одна планка dimm_size
vm.memory.plug("1G")  # возвращает новый максимум, МиБ
vm.memory.dimms()  # [128, 1024]
vm.memory.unplug()  # снять последнюю планку (гость должен её отпустить)
vm.memory.unplug("1G")
```

* **KVM** добавляет модули `pc-dimm` в NUMA-узел 0. Домен определяется с
  `<maxMemory slots=...>` и NUMA-ячейкой — без них QEMU хотплаг не даёт.
* **Xen** не знает DIMM: `plug()` поднимает живой потолок памяти, а xen-балун
  уже расширяет гостя внутри него.

Выход за `max_memory` — `ConfigurationError`; все слоты заняты —
`VMStateError`. Чтобы определить машину без хотплага, задайте `max_memory`
равным `memory` (или `memory_slots=0`).

## vCPU

```python
vm.cpu.count  # vCPU сейчас
vm.cpu.maximum  # max_vcpus (по умолчанию max(vcpus, 8))
vm.cpu.set(4)  # живой хотплаг; на выключенной машине — в конфигурацию
vm.cpu.plug(), vm.cpu.unplug()
vm.cpu.time_ns()  # процессорное время с момента запуска
vm.cpu.usage()  # загрузка с прошлого вызова, 0..100 %
```

`usage()` считается по приращению накопительного `cpu_time` libvirt между
двумя вызовами, делённому на прошедшее время и число vCPU. Первый вызов после
старта, сброса или отката снапшота возвращает `0.0`. У каждой машины свой
счётчик, поэтому потоки мониторинга не путают машины между собой.

## Один замер метрик

```python
m = vm.metrics()  # GuestMetrics
m.state, m.cpu_percent, m.vcpus
m.memory  # MemoryStats или None, если гость выключен
m.disks["vda"].read_bytes
```

Замер снимается под замком машины, поэтому значения согласованы между собой.
Адаптивный регулятор обычно вызывает `metrics()` по таймеру и реагирует через
`memory.set()` / `memory.plug()` / `cpu.set()`.
