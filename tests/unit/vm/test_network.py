from azarovo_hyper import VMState


def test_network_queries(running, fake):
    assert running.network.interfaces() == []
    iface = fake.domains(running.uri)[running.name].tree.find("./devices/interface")
    target = iface.makeelement("target", {"dev": "vnet7"})
    iface.append(target)
    assert running.network.interfaces() == ["vnet7"]
    assert running.network.addresses() == {"eth0": ["10.0.2.15"]}
    stats = running.network.stats()["vnet7"]
    assert (stats.rx_bytes, stats.tx_bytes, stats.tx_packets) == (10, 20, 2)


def test_metrics(running, vm):
    sample = running.metrics()
    assert sample.state is VMState.RUNNING
    assert sample.memory.actual_mib == 1024
    assert set(sample.disks) == {"vda"}
    running.stop()
    stopped = running.metrics()
    assert stopped.memory is None and stopped.cpu_percent == 0
