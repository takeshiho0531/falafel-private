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
async def monitor_req_from_lsu(
    dut, expected_addr=None, expected_data=None, expected_is_write=0
):
    while True:
        await ReadOnly()
        if dut.mem_req_val_o.value == 1:
            if expected_addr is not None:
                assert dut.mem_req_addr_o == expected_addr, int(
                    dut.mem_req_addr_o
                )  # noqa
            if expected_data is not None:
                assert dut.mem_req_data_o == expected_data, int(
                    dut.mem_req_data_o
                )  # noqa
            if expected_is_write != 0:
                assert dut.mem_req_is_write_o == 1
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

    def update_size(self, addr, size):
        if addr in self.nodes:
            self.nodes[addr].size = size
        else:
            print(f"Node with address {addr} does not exist.")

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
        for addr, node in sorted(self.nodes.items()):
            print(
                f"Addr: {addr}, Size: {node.size}, Next Addr: {node.next_addr}"
            )  # noqa


async def grant_store(dut, clk):
    dut.mem_req_rdy_i.setimmediatevalue(0)
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(0)
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)
    dut.mem_req_rdy_i.setimmediatevalue(1)


async def send_rsp_from_mem(
    dut, clk, addr, linked_list: LinkedList, data, expected_next_addr=None
):
    if (addr - 8) in linked_list.nodes:
        # store updated only next_addr
        linked_list.update_next_addr(addr - 8, data)
        await FallingEdge(clk)
        await grant_store(dut, clk)
    elif (addr) in linked_list.nodes:
        # store updated size
        linked_list.update_size(addr, data)
        await FallingEdge(clk)
        await grant_store(dut, clk)
        assert dut.mem_req_data_o == expected_next_addr, int(dut.mem_req_data_o)  # noqa
        linked_list.update_next_addr(addr, int(dut.mem_req_data_o))
        await FallingEdge(clk)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await grant_store(dut, clk)
    else:  # store updated size
        linked_list.add_node(addr, data)
        await FallingEdge(clk)
        await grant_store(dut, clk)
        assert dut.mem_req_data_o == expected_next_addr, int(dut.mem_req_data_o)  # noqa
        linked_list.update_next_addr(addr, int(dut.mem_req_data_o))
        await FallingEdge(clk)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await grant_store(dut, clk)

    await FallingEdge(clk)
    dut.mem_req_rdy_i.setimmediatevalue(1)
    await FallingEdge(clk)


async def send_load_rsp_from_mem(dut, clk, addr, linked_list: LinkedList):
    if (dut.mem_req_addr_o.value.integer - 8) in linked_list.nodes:
        await send_next_addr_from_mem(dut, clk, addr, linked_list)
    else:
        await FallingEdge(clk)
        await send_size_from_mem(dut, clk, addr, linked_list)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await send_next_addr_from_mem(dut, clk, addr, linked_list)

    await FallingEdge(clk)
    dut.mem_req_rdy_i.setimmediatevalue(1)
    await FallingEdge(clk)


async def send_size_from_mem(dut, clk, addr, linked_list: LinkedList):
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(linked_list.get_node(addr)[0])
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)


async def send_next_addr_from_mem(dut, clk, addr, linked_list: LinkedList):
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(linked_list.get_node(addr)[1])
    await FallingEdge(clk)
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
    expected_addr = 16
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the second header
    expected_addr = 300
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the third header
    expected_addr = 500
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    print("-----finish loading / finding fit-----")

    # updating the allocated block (storing size & next_addr)
    expected_addr = 500
    expected_data = 200
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=1
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_rsp_from_mem(
        dut,
        clk,
        expected_addr,
        linked_list,
        expected_data,
        expected_next_addr=0,  # noqa
    )
    print("-----Granted updating the allocated block-----")
    linked_list.print_list()

    # creating the new block (storing size & next_addr)
    expected_addr = 716
    expected_data = 100
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=1
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_rsp_from_mem(
        dut,
        clk,
        expected_addr,
        linked_list,
        expected_data,
        expected_next_addr=2000,  # noqa
    )
    print("-----Granted creating the new block-----")
    linked_list.print_list()

    # adjusting the link
    expected_addr = 308
    expected_data = 716
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=0
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await send_rsp_from_mem(dut, clk, expected_addr, linked_list, expected_data)  # noqa
    print("-----Granted adjusting the link-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")
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

    print("-----Start allocation-----")
    linked_list.print_list()

    # loading first header
    expected_addr = 16
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the second header
    expected_addr = 300
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the third header
    expected_addr = 500
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the forth (last) header
    expected_addr = 2000
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    print("-----finish loading / finding fit-----")

    # updating the allocated block (storing size & next_addr)
    expected_addr = 2000
    expected_data = 200
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=1
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_rsp_from_mem(
        dut,
        clk,
        expected_addr,
        linked_list,
        expected_data,
        expected_next_addr=0,  # noqa
    )
    print("-----Granted updating the allocated block-----")
    linked_list.print_list()

    # creating the new block (storing size & next_addr)
    expected_addr = 2216
    expected_data = 99
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=1
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_rsp_from_mem(
        dut,
        clk,
        expected_addr,
        linked_list,
        expected_data,
        expected_next_addr=0,  # noqa
    )
    print("-----Granted creating the new block-----")
    linked_list.print_list()

    # adjusting the link
    expected_addr = 508
    expected_data = 2216
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=0
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await send_rsp_from_mem(dut, clk, expected_addr, linked_list, expected_data)  # noqa
    print("-----Granted adjusting the link-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")
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

    print("-----Start allocation-----")
    linked_list.print_list()

    # loading first header
    expected_addr = 16
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the second header
    expected_addr = 300
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the third header
    expected_addr = 500
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    print("-----finding block to free-----")

    # loading the freeing header
    expected_addr = 2000
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the right header
    expected_addr = 2216
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # updating the allocated block (storing size & next_addr)
    expected_addr = 2000
    expected_data = 299
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=1
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_rsp_from_mem(
        dut,
        clk,
        expected_addr,
        linked_list,
        expected_data,
        expected_next_addr=0,  # noqa
    )
    print("-----Granted updating the allocated block-----")
    linked_list.print_list()

    # adjusting the link
    expected_addr = 508
    expected_data = 2000
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=0
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await send_rsp_from_mem(dut, clk, expected_addr, linked_list, expected_data)  # noqa
    print("-----Granted adjusting the link-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")
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
    expected_addr = 16
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the second header
    expected_addr = 300
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the third header
    expected_addr = 500
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    print("-----finding block to free-----")

    # loading the freeing header
    expected_addr = 800
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # creating a new (merged) block (size & next_addr)
    expected_addr = 500
    expected_data = 800
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=1
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_rsp_from_mem(
        dut,
        clk,
        expected_addr,
        linked_list,
        expected_data,
        expected_next_addr=2000,  # noqa
    )
    print("-----Granted creating a block-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")
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
    expected_addr = 16
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the second header
    expected_addr = 300
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the third header
    expected_addr = 500
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    print("-----finding block to free-----")

    # loading the freeing header
    expected_addr = 800
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # loading the right header
    expected_addr = 2000
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(dut, expected_addr=expected_addr)
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_load_rsp_from_mem(dut, clk, expected_addr, linked_list)

    # creating a new (merged) block (size & next_addr)
    expected_addr = 500
    expected_data = 1799
    monitor_task_req_from_lsu = cocotb.start_soon(
        monitor_req_from_lsu(
            dut, expected_addr, expected_data, expected_is_write=1
        )  # noqa
    )
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await FallingEdge(clk)
    await send_rsp_from_mem(
        dut,
        clk,
        expected_addr,
        linked_list,
        expected_data,
        expected_next_addr=0,  # noqa
    )
    print("-----Granted creating a block-----")
    linked_list.print_list()

    # releasing the lock
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")
    await FallingEdge(clk)
    await RisingEdge(clk)
