import cocotb
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.clock import Clock

from falafel_bus import FalafelMemRequestBus, FalafelMemRequestMonitor, FalafelMemResponseBus, FalafelMemResponseDriver
from falafel_bus import FalafelFifoReadBus, FalafelFifoWriteBus, FalafelFifoReadSlave, FalafelFifoWriteSlave

import falafel_block
from falafel_block import Block
from falafel_pkg import *


CLK_PERIOD = 10
MAX_SIM_TIME = 10000
UNITS = 'ns'


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


async def mem_monitor(dut, clk, mem):
    mem_req_bus = FalafelMemRequestBus(dut, "mem_req", {'val': 'val_o', 'rdy': 'rdy_i', 'is_write':
                                                        'is_write_i', 'addr': 'addr_o', 'data': 'data_o'})
    mem_rsp_bus = FalafelMemResponseBus(
        dut, "mem_rsp", {'val': 'val_i', 'rdy': 'rdy_o', 'data': 'data_i'})

    mem_req_monitor = FalafelMemRequestMonitor(mem_req_bus, clk)
    mem_rsp_driver = FalafelMemResponseDriver(mem_rsp_bus, clk)

    await RisingEdge(clk)

    while True:
        (is_write, addr, data) = await mem_req_monitor.recv()

        norm_addr = addr//WORD_SIZE

        if is_write:
            # print('mem[norm_addr] =', data)
            mem[norm_addr] = data
        else:
            assert norm_addr in mem, "Accessed uninitialized mem[{}]".format(
                norm_addr)
            # print('mem[' + str(norm_addr) + '] =', mem[norm_addr])
            data = mem[norm_addr]

        await mem_rsp_driver.send(data)


@cocotb.test()
async def test_simple_alloc(dut):
    """Test simple allocations"""

    clk = dut.clk_i

    cocotb.start_soon(Clock(clk, CLK_PERIOD, units=UNITS).start())

    alloc_fifo_bus = FalafelFifoReadBus(
        dut, "alloc_fifo", {'empty': 'empty_i', 'read': 'read_o', 'dout': 'dout_i'})

    free_fifo_bus = FalafelFifoReadBus(
        dut, "free_fifo", {'empty': 'empty_i', 'read': 'read_o', 'dout': 'dout_i'})

    resp_fifo_bus = FalafelFifoWriteBus(
        dut, "resp_fifo", {'full': 'full_i', 'write': 'write_o', 'din': 'din_o'})

    alloc_fifo_driver = FalafelFifoReadSlave(alloc_fifo_bus, clk)
    free_fifo_driver = FalafelFifoReadSlave(free_fifo_bus, clk)
    resp_fifo_driver = FalafelFifoWriteSlave(resp_fifo_bus, clk)

    free_list_ptr = 0x20
    dut.falafel_config_free_list_ptr.value = free_list_ptr

    mem = {}

    blocks = [
        Block(160, 32),
        Block(320, 128),
        Block(1000, 32),
        Block(2000, 56)
    ]

    falafel_block.list_to_mem(free_list_ptr, blocks, mem)

    await reset_dut(dut, clk)
    await cocotb.start(sim_time_counter(dut, clk))
    await cocotb.start(mem_monitor(dut, clk, mem))
    await cocotb.start(alloc_fifo_driver.monitor())
    await cocotb.start(free_fifo_driver.monitor())
    await cocotb.start(resp_fifo_driver.monitor())

    await Timer(20, units=UNITS)

    # print('initial list', end=' ')
    # falafel_block.print_list(blocks)

    await alloc_fifo_driver.push(35)
    await alloc_fifo_driver.push(32)
    await alloc_fifo_driver.push(100)
    await alloc_fifo_driver.push(80)
    await alloc_fifo_driver.push(32)
    await alloc_fifo_driver.push(50)
    await alloc_fifo_driver.push(32)

    ptr = await resp_fifo_driver.pop()
    assert ptr == 328, 'ptrs dont match'
    ptr = await resp_fifo_driver.pop()
    assert ptr == 168, 'ptrs dont match'
    ptr = await resp_fifo_driver.pop()
    assert ptr == ERR_NOMEM, 'ptrs dont match'
    ptr = await resp_fifo_driver.pop()
    assert ptr == 376, 'ptrs dont match'
    ptr = await resp_fifo_driver.pop()
    assert ptr == 1008, 'ptrs dont match'
    ptr = await resp_fifo_driver.pop()
    assert ptr == 2008, 'ptrs dont match'
    ptr = await resp_fifo_driver.pop()
    assert ptr == ERR_NOMEM, 'ptrs dont match'

    await Timer(100, units=UNITS)
    # print('final list', end=' ')
    # falafel_block.print_list(falafel_block.mem_to_list(free_list_ptr, mem))

    await Timer(100, units=UNITS)


@cocotb.test()
async def test_simple_frees(dut):
    """Test simple frees"""

    clk = dut.clk_i

    cocotb.start_soon(Clock(clk, CLK_PERIOD, units=UNITS).start())

    request_bus = FalafelValRdyBus(
        dut, "req", {'val': 'val_i', 'rdy': 'rdy_o', 'data': 'data_i'})

    response_bus = FalafelValRdyBus(
        dut, "resp", {'val': 'val_o', 'rdy': 'rdy_i', 'data': 'data_o'})

    req_driver = FalafelValRdyDriver(request_bus, clk)
    resp_monitor = FalafelValRdyMonitor(response_bus, clk)

    free_list_ptr = 0x20

    mem = {}

    blocks = [
        Block(160, 32),
        Block(320, 128),
        Block(1000, 32),
        Block(2000, 56)
    ]

    falafel_block.list_to_mem(free_list_ptr, blocks, mem)

    await reset_dut(dut, clk)
    await cocotb.start(sim_time_counter(dut, clk))
    await cocotb.start(mem_monitor(dut, clk, mem))
    await Timer(20, units=UNITS)

    # print('initial list', end=' ')
    # falafel_block.print_list(blocks)

    # configure free ptr
    await req_driver.send(REQ_ACCESS_REGISTER)
    await req_driver.send(FREE_LIST_PTR_ADDR)
    await req_driver.send(free_list_ptr)

    await req_driver.send(REQ_ALLOC_MEM)
    await req_driver.send(5)

    ptr = await resp_monitor.recv()
    print('ptr', ptr)

    # print('final list', end=' ')
    # falafel_block.print_list(falafel_block.mem_to_list(free_list_ptr, mem))

    await Timer(100, units=UNITS)
