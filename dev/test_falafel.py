import cocotb
from cocotb.triggers import FallingEdge, ReadOnly, Timer, RisingEdge
from cocotb.clock import Clock

CLK_PERIOD = 10
MAX_SIM_TIME = 15000
UNITS = "ns"


async def reset_dut(dut, clk):
    await FallingEdge(clk)

    clk.value = 0
    dut.rst_ni.value = 0

    for i in range(10):
        await FallingEdge(clk)
    dut.rst_ni.value = 1

    await FallingEdge(clk)
    await FallingEdge(clk)


@cocotb.coroutine
async def monitor_req_from_lsu(dut):
    while True:
        await ReadOnly()
        if dut.mem_req_val_o.value == 1:
            dut._log.info("mem_req_val_o is now 1")
            break
        await Timer(1, units="ns")


@cocotb.coroutine
async def monitor_falafel_ready(dut):
    while True:
        await ReadOnly()
        if dut.mem_rsp_rdy_o.value == 1:
            dut._log.info("mem_rsp_rdy_o is now 1")
            break
        await Timer(1, units="ns")


async def send_req_to_allocate(dut, clk):
    await FallingEdge(clk)
    dut.is_alloc_i.setimmediatevalue(1)
    dut.req_alloc_valid_i.setimmediatevalue(1)
    dut.size_to_allocate_i.setimmediatevalue(200)
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.req_alloc_valid_i.setimmediatevalue(0)


async def send_req_to_free(dut, clk, addr_to_free):
    await FallingEdge(clk)
    dut.is_alloc_i.setimmediatevalue(0)
    dut.req_alloc_valid_i.setimmediatevalue(1)
    dut.addr_to_free_i.setimmediatevalue(addr_to_free)
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.req_alloc_valid_i.setimmediatevalue(0)


class Node:
    def __init__(self, addr, size, next_addr=None):
        self.addr = addr
        self.size = size
        self.next_addr = next_addr

    def __str__(self):
        return f"Node(addr={self.addr}, size={self.size}, next_addr={self.next_addr})"  # noqa


class LinkedList:
    def __init__(self):
        self.nodes = {}

    def add_node(self, addr, size, next_addr=None):
        node = Node(addr, size, next_addr)
        self.nodes[addr] = node

    def update_next_addr(self, addr, next_addr):
        if addr in self.nodes:
            self.nodes[addr].next_addr = next_addr
        else:
            print(f"Node with address {addr} does not exist.")

    def get_node(self, addr):
        if addr in self.nodes:
            node = self.nodes[addr]
            return node.size, node.next_addr
        else:
            return None, None

    def print_list(self):
        print("LinkedList contents:")
        for addr, node in self.nodes.items():
            print(
                f"Addr: {addr}, Size: {node.size}, Next Addr: {node.next_addr}"
            )  # noqa


async def send_rsp_from_mem(dut, clk, addr, linked_list: LinkedList, data=None):
    if dut.mem_req_is_write_o == 1:  # store
        if (addr - 8) in linked_list.nodes:
            # store only updated next_addr
            linked_list.update_next_addr(addr - 8, data)
        else:
            linked_list.add_node(addr, data)

        await FallingEdge(clk)
        await RisingEdge(clk)
        await FallingEdge(clk)
        await grant_lock(dut, clk)
        await FallingEdge(clk)
        await RisingEdge(clk)
    else:  # load
        if (dut.mem_req_addr_o.value.integer - 8) in linked_list.nodes:
            await send_next_addr_from_mem(dut, clk, addr, linked_list)
        else:
            await FallingEdge(clk)
            await send_size_from_mem(dut, clk, addr, linked_list)
            await FallingEdge(clk)
            await RisingEdge(clk)
            await FallingEdge(clk)
            await RisingEdge(clk)
            await FallingEdge(clk)
            await send_next_addr_from_mem(dut, clk, addr, linked_list)

    await FallingEdge(clk)
    dut.mem_req_rdy_i.setimmediatevalue(1)
    await FallingEdge(clk)
    await RisingEdge(clk)


async def send_size_from_mem(dut, clk, addr, linked_list: LinkedList):
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(linked_list.get_node(addr)[0])
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)


async def send_next_addr_from_mem(dut, clk, addr, linked_list: LinkedList):
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(linked_list.get_node(addr)[1])
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)


async def grant_lock(dut, clk):
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    dut.mem_req_rdy_i.setimmediatevalue(0)
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(0)
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)
    dut.mem_req_rdy_i.setimmediatevalue(1)


@cocotb.test()
async def test_falafel_alloc_first_fit(dut):
    print("---------------------- Start first fit test ----------------------")
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())
    dut.config_alloc_strategy_i.setimmediatevalue(0)  # first fit

    monitor_task_req_from_lsu = cocotb.start_soon(monitor_req_from_lsu(dut))
    monitor_task_falafel_ready = cocotb.start_soon(monitor_falafel_ready(dut))

    linked_list = LinkedList()
    linked_list.add_node(16, 160, 300)
    linked_list.add_node(300, 100, 500)
    linked_list.add_node(500, 300, 2000)
    linked_list.add_node(2000, 500, 3000)

    await reset_dut(dut, clk)

    dut.mem_req_rdy_i.setimmediatevalue(1)
    dut.mem_rsp_val_i.setimmediatevalue(0)

    for i in range(10):
        await FallingEdge(clk)

    # Send request to allocate
    assert dut.mem_rsp_rdy_o == 1
    await send_req_to_allocate(dut, clk)
    print("Sent request to allocate")

    # Wait for the lock request
    await monitor_task_req_from_lsu
    await grant_lock(dut, clk)
    print("Granted lock")

    await monitor_task_req_from_lsu
    await monitor_task_falafel_ready
    await grant_lock(dut, clk)
    print("Granted cas")

    print("-----Start allocation-----")
    linked_list.print_list()

    # loading first header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 16, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the second header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 300, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the third header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 500
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # updating the allocated block (size)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 500, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 200
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)

    # updating the allocated block (next addr)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 508, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)  # TODO
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted updating the allocated block-----")
    linked_list.print_list()

    # creating the new block (setting size)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 716, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 100
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)

    # creating the new block (setting next_addr)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 724, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted creating the new block-----")
    linked_list.print_list()

    # adjusting the link
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 308, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 716, int(dut.mem_req_data_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted adjusting the link-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")  # TODO
    await FallingEdge(clk)
    await RisingEdge(clk)


@cocotb.test()
async def test_falafel_alloc_best_fit(dut):
    print("---------------------- Start best fit test ----------------------")
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())
    dut.config_alloc_strategy_i.setimmediatevalue(1)  # best fit

    monitor_task_req_from_lsu = cocotb.start_soon(monitor_req_from_lsu(dut))
    monitor_task_falafel_ready = cocotb.start_soon(monitor_falafel_ready(dut))

    linked_list = LinkedList()
    linked_list.add_node(16, 160, 300)
    linked_list.add_node(300, 100, 500)
    linked_list.add_node(500, 300, 2000)
    linked_list.add_node(2000, 299, 0)
    linked_list.print_list()

    await reset_dut(dut, clk)

    dut.mem_req_rdy_i.setimmediatevalue(1)
    dut.mem_rsp_val_i.setimmediatevalue(0)

    for i in range(10):
        await FallingEdge(clk)

    # Send request to allocate
    assert dut.mem_rsp_rdy_o == 1
    await send_req_to_allocate(dut, clk)
    print("Sent request to allocate")

    # Wait for the lock request
    await monitor_task_req_from_lsu
    await grant_lock(dut, clk)
    print("Granted lock")

    await monitor_task_req_from_lsu
    await monitor_task_falafel_ready
    await grant_lock(dut, clk)
    print("Granted cas")

    # loading first header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 16, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the second header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 300, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the  third header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 500
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    linked_list.print_list()

    # loading the forth (the last) header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 2000
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    linked_list.print_list()

    # updating the allocated block (size)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2000, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 200
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)

    # updating the allocated block (next addr)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2008, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)  # TODO
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted updating the allocated block-----")
    linked_list.print_list()

    # creating the new block (setting size)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2216, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 99
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)

    # creating the new block (setting next_addr)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2224, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted creating the new block-----")
    linked_list.print_list()

    # adjusting the link
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 508, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 2216, int(dut.mem_req_data_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted adjusting the link-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")  # TODO
    await FallingEdge(clk)
    await RisingEdge(clk)


@cocotb.test()
async def test_falafel_free_merge_right(dut):
    print("------------------ Start free merge right test ------------------")
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())

    monitor_task_req_from_lsu = cocotb.start_soon(monitor_req_from_lsu(dut))
    monitor_task_falafel_ready = cocotb.start_soon(monitor_falafel_ready(dut))

    linked_list = LinkedList()
    linked_list.add_node(16, 160, 300)
    linked_list.add_node(300, 100, 500)
    linked_list.add_node(500, 300, 2216)
    linked_list.add_node(2000, 200, 0)
    linked_list.add_node(2216, 83, 0)
    linked_list.print_list()

    await reset_dut(dut, clk)

    dut.mem_req_rdy_i.setimmediatevalue(1)
    dut.mem_rsp_val_i.setimmediatevalue(0)

    for i in range(10):
        await FallingEdge(clk)

    # send req to free
    assert dut.mem_rsp_rdy_o == 1
    await send_req_to_free(dut, clk, 2000)
    print("Sent request to free")

    # Wait for the lock request
    await monitor_task_req_from_lsu
    await grant_lock(dut, clk)
    print("Granted lock")

    await monitor_task_req_from_lsu
    await monitor_task_falafel_ready
    await grant_lock(dut, clk)
    print("Granted cas")

    print("-----Start freeing-----")
    linked_list.print_list()

    # loading first header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 16, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the second header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 300, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the third header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 500
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the freeing header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 2000
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the right header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 2216
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # creating a new (merged) block (size)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2000, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 299
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)

    # creating a new (merged) block (next addr)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2008, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted creating a new merged block header-----")
    linked_list.print_list()

    # adjusting the link
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 508, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 2000, int(dut.mem_req_data_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted adjusting the link-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")  # TODO
    await FallingEdge(clk)
    await RisingEdge(clk)


@cocotb.test()
async def test_falafel_free_merge_left(dut):
    print("------------------ Start free merge left test ------------------")
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())

    monitor_task_req_from_lsu = cocotb.start_soon(monitor_req_from_lsu(dut))
    monitor_task_falafel_ready = cocotb.start_soon(monitor_falafel_ready(dut))

    linked_list = LinkedList()
    linked_list.add_node(16, 160, 300)
    linked_list.add_node(300, 100, 500)
    linked_list.add_node(500, 284, 2000)
    linked_list.add_node(800, 500, 0)
    linked_list.add_node(2000, 299, 0)
    linked_list.print_list()

    await reset_dut(dut, clk)

    dut.mem_req_rdy_i.setimmediatevalue(1)
    dut.mem_rsp_val_i.setimmediatevalue(0)

    for i in range(10):
        await FallingEdge(clk)

    # send req to free
    # assert dut.mem_rsp_rdy_o == 1
    dut.mem_rsp_rdy_o.setimmediatevalue(1)
    await send_req_to_free(dut, clk, 800)
    print("Sent request to free")

    # Wait for the lock request
    await monitor_task_req_from_lsu
    await grant_lock(dut, clk)
    print("Granted lock")

    await monitor_task_req_from_lsu
    await monitor_task_falafel_ready
    await grant_lock(dut, clk)
    print("Granted cas")

    print("-----Start freeing-----")
    linked_list.print_list()

    # loading first header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 16, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the second header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 300, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the third header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 500
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the freeing header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 800
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # creating a new (merged) block (size)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 500, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 800
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)

    # creating a new (merged) block (next addr)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 508, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 2000, int(dut.mem_req_data_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted creating a new merged block header-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")  # TODO
    await FallingEdge(clk)
    await RisingEdge(clk)


@cocotb.test()
async def test_falafel_free_merge_both_sides(dut):
    print("---------------- Start free merge both sides test ----------------")
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())

    monitor_task_req_from_lsu = cocotb.start_soon(monitor_req_from_lsu(dut))
    monitor_task_falafel_ready = cocotb.start_soon(monitor_falafel_ready(dut))

    linked_list = LinkedList()
    linked_list.add_node(16, 160, 300)
    linked_list.add_node(300, 100, 500)
    linked_list.add_node(500, 284, 2000)
    linked_list.add_node(800, 1184, 2000)  # TODO
    linked_list.add_node(2000, 299, 0)
    linked_list.print_list()

    await reset_dut(dut, clk)

    dut.mem_req_rdy_i.setimmediatevalue(1)
    dut.mem_rsp_val_i.setimmediatevalue(0)

    for i in range(10):
        await FallingEdge(clk)

    # send req to free
    # assert dut.mem_rsp_rdy_o == 1
    dut.mem_rsp_rdy_o.setimmediatevalue(1)
    await send_req_to_free(dut, clk, 800)
    print("Sent request to free")

    # Wait for the lock request
    await monitor_task_req_from_lsu
    await grant_lock(dut, clk)
    print("Granted lock")

    await monitor_task_req_from_lsu
    await monitor_task_falafel_ready
    await grant_lock(dut, clk)
    print("Granted cas")

    print("-----Start freeing-----")
    linked_list.print_list()

    # loading first header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 16, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the second header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 300, int(dut.mem_req_addr_o)
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the third header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 500
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the freeing header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 800
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)

    # loading the right header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_addr_o == 2000
    addr = int(dut.mem_req_addr_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list)
    print("Sent size of the right header from mem, size:", 299)

    # creating a new (merged) block (size)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 500, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 1799
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)

    # creating a new (merged) block (next addr)
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 508, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    addr = int(dut.mem_req_addr_o)
    data = int(dut.mem_req_data_o)
    await send_rsp_from_mem(dut, clk, addr, linked_list, data)
    print("-----Granted creating a new merged block header-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")  # TODO
    await FallingEdge(clk)
    await RisingEdge(clk)
