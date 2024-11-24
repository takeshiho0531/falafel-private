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


async def sim_time_counter(dut, clk):
    counter = 0

    while counter < MAX_SIM_TIME:
        counter += 1
        await FallingEdge(clk)

    assert False, "Surpassed MAX_SIM_TIME of " + str(MAX_SIM_TIME)


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
    dut.req_alloc_valid_i.setimmediatevalue(1)
    dut.size_to_allocate_i.setimmediatevalue(200)
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
    print("dut.mem_rsp_val_i == 1", dut.mem_rsp_val_i == 1)
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)
    print("dut.mem_rsp_val_i == 0", dut.mem_rsp_val_i == 0)
    dut.mem_req_rdy_i.setimmediatevalue(1)


@cocotb.test()
async def test_falafel(dut):
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())

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

    # Wait for the request for the first header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_val_o == 1
    assert dut.mem_req_addr_o == 16, int(dut.mem_req_addr_o)
    await FallingEdge(clk)  # it seems to be necessary
    await send_size_from_mem(dut, clk, addr=16, linked_list=linked_list)  # noqa
    print("Sent size of the first header from mem, size:", linked_list.get_node(16)[0])
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    await send_next_addr_from_mem(dut, clk, addr=16, linked_list=linked_list)  # noqa
    print(
        "Sent next addr of the first header from mem, next addr:",
        linked_list.get_node(16)[1],
    )
    await FallingEdge(clk)
    await RisingEdge(clk)

    # # Wait for the request for second header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_val_o == 1
    assert dut.mem_req_addr_o == 300
    await FallingEdge(clk)  # it seems to be necessary
    await send_size_from_mem(dut, clk, addr=300, linked_list=linked_list)  # noqa
    print(
        "Sent size of the second header from mem, size:", linked_list.get_node(300)[0]
    )
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    await send_next_addr_from_mem(dut, clk, addr=300, linked_list=linked_list)  # noqa
    print(
        "Sent next addr of the second header from mem, next addr:",
        linked_list.get_node(300)[1],
    )
    await FallingEdge(clk)
    await RisingEdge(clk)

    # # Wait for the request for third header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_val_o == 1
    assert dut.mem_req_addr_o == 500
    await FallingEdge(clk)  # it seems to be necessary
    await send_size_from_mem(dut, clk, addr=500, linked_list=linked_list)  # noqa
    print("Sent size of the third header from mem, size:", linked_list.get_node(500)[0])
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    await send_next_addr_from_mem(dut, clk, addr=500, linked_list=linked_list)  # noqa
    print(
        "Sent next addr of the third header from mem, next addr:",
        linked_list.get_node(500)[1],
    )
    await FallingEdge(clk)
    await RisingEdge(clk)

    linked_list.print_list()

    # # Wait for the request for forth (last) header
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_val_o == 1
    assert dut.mem_req_addr_o == 2000
    await FallingEdge(clk)  # it seems to be necessary
    await send_size_from_mem(dut, clk, addr=2000, linked_list=linked_list)  # noqa
    print(
        "Sent size of the third header from mem, size:", linked_list.get_node(2000)[0]
    )
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    await send_next_addr_from_mem(dut, clk, addr=2000, linked_list=linked_list)  # noqa
    print(
        "Sent next addr of the third header from mem, next addr:",
        linked_list.get_node(500)[1],
    )
    await FallingEdge(clk)
    await RisingEdge(clk)

    linked_list.print_list()

    # Wait for insert req
    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    assert dut.mem_req_val_o == 1
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2264, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 99
    await FallingEdge(clk)
    await grant_lock(dut, clk)
    print("Granted size update")
    await FallingEdge(clk)
    await RisingEdge(clk)
    # linked_list.print_list()

    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    # assert dut.mem_req_val_o == 1 # TODO
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 2272, int(dut.mem_req_addr_o)
    await grant_lock(dut, clk)
    print("Granted next addr update")
    await FallingEdge(clk)
    await RisingEdge(clk)

    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    # await RisingEdge(clk)
    # await FallingEdge(clk)
    assert dut.mem_req_val_o == 1
    assert dut.mem_req_is_write_o == 1
    assert dut.mem_req_addr_o == 508, int(dut.mem_req_addr_o)
    assert dut.mem_req_data_o == 2264, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted delete")
    await FallingEdge(clk)
    await RisingEdge(clk)

    await monitor_task_req_from_lsu
    await FallingEdge(clk)
    assert dut.mem_req_data_o == 0, int(dut.mem_req_data_o)
    await grant_lock(dut, clk)
    print("Granted release lock")  # TODO
    await FallingEdge(clk)
    await RisingEdge(clk)

    for i in range(10):
        await FallingEdge(clk)

    assert True
