import cocotb
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.clock import Clock

from falafel_bus import FalafelMemRequestBus, FalafelMemRequestMonitor, FalafelMemResponseBus, FalafelMemResponseDriver
from falafel_bus import FalafelFifoReadBus, FalafelFifoWriteBus, FalafelFifoReadSlave, FalafelFifoWriteSlave

import falafel_block
from falafel_block import Block


CLK_PERIOD = 10
MAX_SIM_TIME = 10000
UNITS = 'ns'
WORD_SIZE = 8


def init_mem():
    mem = {}

    def store_block(addr, block):
        addr = addr//WORD_SIZE
        (size, next_ptr) = block
        mem[addr] = size
        mem[addr+1] = next_ptr

    def store_word(addr, word):
        addr = addr//WORD_SIZE
        mem[addr] = word

    NULL_PTR = 0

    store_word(0x20, 160)
    store_block(160, (10, 320))
    store_block(320, (48, 1000))
    store_block(1000, (32, NULL_PTR))

    return mem


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

    # mem = init_mem()

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
    """Test simple allocation"""

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
        Block(160, 10),
        Block(320, 128),
        # Block(320, 32),
        # Block(320, 72),
        Block(1000, 32),
        Block(2000, 50)
    ]

    # expected_blocks = [
    #     Block(160, 10),
    #     Block(320, 128),
    #     Block(1000, 32),
    #     Block(2000, 50)
    # ]

    # print('initial list', blocks)
    print('initial list', end=' ')
    falafel_block.print_list(blocks)

    falafel_block.list_to_mem(free_list_ptr, blocks, mem)

    await reset_dut(dut, clk)
    await cocotb.start(sim_time_counter(dut, clk))
    await cocotb.start(mem_monitor(dut, clk, mem))
    await cocotb.start(alloc_fifo_driver.monitor())
    await cocotb.start(free_fifo_driver.monitor())
    await cocotb.start(resp_fifo_driver.monitor())

    await Timer(20, units=UNITS)

    await alloc_fifo_driver.push(35)
    ptr = await resp_fifo_driver.pop()
    print('ptr:', ptr)
    await Timer(1000, units=UNITS)
    print('middle list', end=' ')
    falafel_block.print_list(falafel_block.mem_to_list(free_list_ptr, mem))
    print('mem[368] =', mem[368//WORD_SIZE])
    print('mem[320] =', mem[320//WORD_SIZE])

    await free_fifo_driver.push(ptr)
    await Timer(1000, units=UNITS)
    print('final list', end=' ')
    falafel_block.print_list(falafel_block.mem_to_list(free_list_ptr, mem))
    print('mem[368] =', mem[368//WORD_SIZE])
    print('mem[320] =', mem[320//WORD_SIZE])

    await Timer(100, units=UNITS)
