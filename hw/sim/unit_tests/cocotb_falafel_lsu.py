import cocotb
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.clock import Clock

from falafel_bus import FalafelMemRequestBus, FalafelMemRequestMonitor, FalafelMemResponseBus, FalafelMemResponseDriver
from falafel_bus import FalafelLsuRequestBus, FalafelLsuResponseBus, FalafelLsuRequestDriver, FalafelLsuResponseMonitor

CLK_PERIOD = 10
MAX_SIM_TIME = 10000
UNITS = 'ns'


def init_mem():
    return {}


async def reset_dut(dut, clk):
    await FallingEdge(clk)

    clk.value = 0
    dut.rst_ni.value = 0

    for i in range(10):
        await FallingEdge(clk)
    dut.rst_ni.value = 1

    await FallingEdge(clk)
    await FallingEdge(clk)


async def sim_time_counter(dut, clk):
    counter = 0

    while counter < MAX_SIM_TIME:
        counter += 1
        await FallingEdge(clk)

    assert False, "Surpassed MAX_SIM_TIME of " + str(MAX_SIM_TIME)


async def mem_monitor(dut, clk):
    mem_req_bus = FalafelMemRequestBus(dut, "mem_req", {'val': 'val_o', 'rdy': 'rdy_i', 'is_write':
                                                        'is_write_i', 'addr': 'addr_o', 'data': 'data_o'})
    mem_rsp_bus = FalafelMemResponseBus(
        dut, "mem_rsp", {'val': 'val_i', 'rdy': 'rdy_o', 'data': 'data_i'})

    mem_req_monitor = FalafelMemRequestMonitor(mem_req_bus, clk)
    mem_rsp_driver = FalafelMemResponseDriver(mem_rsp_bus, clk)

    await RisingEdge(clk)

    mem = init_mem()

    while True:
        (is_write, addr, data) = await mem_req_monitor.recv()

        norm_addr = addr/8

        if is_write:
            mem[norm_addr] = data
        else:
            assert norm_addr in mem, "Accessed uninitialized mem[{}]".format(
                norm_addr)
            data = mem[norm_addr]

        await mem_rsp_driver.send(data)


@cocotb.test()
async def test_load_store_words(dut):
    """Test loading and storing words"""

    clk = dut.clk_i

    cocotb.start_soon(Clock(clk, CLK_PERIOD, units=UNITS).start())

    lsu_req_bus = FalafelLsuRequestBus(
        dut, "alloc_req", {'val': 'val_i', 'rdy': 'rdy_o', 'op': 'op_i',
                           'addr': 'addr_i', 'word': 'word_i', 'block_size':
                           'block_size_i', 'block_next_ptr': 'block_next_ptr_i'})

    lsu_rsp_bus = FalafelLsuResponseBus(
        dut, "alloc_rsp", {'val': 'val_o', 'rdy': 'rdy_i', 'word': 'word_o',
                           'block_size': 'block_size_o', 'block_next_ptr':
                           'block_next_ptr_o'})

    lsu_req_driver = FalafelLsuRequestDriver(lsu_req_bus, clk)
    lsu_rsp_monitor = FalafelLsuResponseMonitor(lsu_rsp_bus, clk)

    await reset_dut(dut, clk)

    await cocotb.start(sim_time_counter(dut, clk))
    await cocotb.start(mem_monitor(dut, clk))

    SIZE = 10
    addr = [i+5 for i in range(SIZE)]
    data = [i+1 for i in range(SIZE)]

    for (a, d) in zip(addr, data):
        await lsu_req_driver.store_word(a, d)
        await lsu_rsp_monitor.recv()

    for (a, d) in zip(addr, data):
        await lsu_req_driver.load_word(a)
        (w, _) = await lsu_rsp_monitor.recv()

        assert w == d, "values don't match"

    await Timer(100, units=UNITS)


@cocotb.test()
async def test_load_store_blocks(dut):
    """Test loading and storing blocks"""

    clk = dut.clk_i

    cocotb.start_soon(Clock(clk, CLK_PERIOD, units=UNITS).start())

    lsu_req_bus = FalafelLsuRequestBus(
        dut, "alloc_req", {'val': 'val_i', 'rdy': 'rdy_o', 'op': 'op_i',
                           'addr': 'addr_i', 'word': 'word_i', 'block_size':
                           'block_size_i', 'block_next_ptr': 'block_next_ptr_i'})

    lsu_rsp_bus = FalafelLsuResponseBus(
        dut, "alloc_rsp", {'val': 'val_o', 'rdy': 'rdy_i', 'word': 'word_o',
                           'block_size': 'block_size_o', 'block_next_ptr':
                           'block_next_ptr_o'})

    lsu_req_driver = FalafelLsuRequestDriver(lsu_req_bus, clk)
    lsu_rsp_monitor = FalafelLsuResponseMonitor(lsu_rsp_bus, clk)

    await reset_dut(dut, clk)

    await cocotb.start(sim_time_counter(dut, clk))
    await cocotb.start(mem_monitor(dut, clk))

    SIZE = 10
    addr = [16*i for i in range(SIZE)]
    data = [(i, 2*i) for i in range(SIZE)]

    for (a, d) in zip(addr, data):
        await lsu_req_driver.store_block(a, d)
        await lsu_rsp_monitor.recv()

    for (a, d) in zip(addr, data):
        await lsu_req_driver.load_block(a)
        (_, b) = await lsu_rsp_monitor.recv()

        assert b == d, "values don't match"

    await Timer(100, units=UNITS)
