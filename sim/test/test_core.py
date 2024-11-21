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


async def send_req_to_allocate(dut, clk):
    dut.req_alloc_valid_i = 1
    dut.size_to_allocate_i = 20
    await FallingEdge(clk)
    dut.req_alloc_valid_i = 0


async def send_metadata_as_rsp(dut, clk, size, addr, next_addr):
    dut.metadata_rsp_val_i = 1
    dut.metadata_rsp_size_i = size
    dut.metadata_rsp_addr_i = addr
    dut.metadata_rsp_next_addr_i = next_addr
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.metadata_rsp_val_i = 0


@cocotb.coroutine
async def monitor_metadata_req(dut):
    while True:
        await ReadOnly()
        if dut.metadata_req_val_o.value == 1:
            dut._log.info("metadata_req_val_o is now 1")
            break
        await Timer(1, units="ns")


@cocotb.test()
async def test_core(dut):
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())
    monitor_task_metadata_req = cocotb.start_soon(monitor_metadata_req(dut))

    await reset_dut(dut, clk)
    cocotb.start(sim_time_counter(dut, clk))

    for i in range(10):
        await FallingEdge(clk)

    await send_req_to_allocate(dut, clk)

    await monitor_task_metadata_req
    assert dut.metadata_req_which_req_o.value == 0

    await FallingEdge(clk)
    await RisingEdge(clk)
    await send_metadata_as_rsp(dut, clk, size=16, addr=0x2, next_addr=0x80)  # lock ok

    await monitor_task_metadata_req
    await FallingEdge(clk)
    # assert dut.metadata_req_which_req_o.value == 1
    await RisingEdge(clk)
    await send_metadata_as_rsp(
        dut, clk, size=16, addr=0x2, next_addr=0x80
    )  # first load ok

    await monitor_task_metadata_req
    # assert dut.metadata_req_addr_o.value == 0x80

    await FallingEdge(clk)
    await RisingEdge(clk)
    await send_metadata_as_rsp(dut, clk, size=18, addr=0x80, next_addr=0x120)

    await monitor_task_metadata_req
    # assert dut.metadata_req_addr_o.value == 0x120

    await FallingEdge(clk)
    await RisingEdge(clk)
    await send_metadata_as_rsp(dut, clk, size=120, addr=0x120, next_addr=0x400)

    await monitor_task_metadata_req
    # assert dut.metadata_req_which_req_o.value == 1

    await FallingEdge(clk)
    await RisingEdge(clk)
    await send_metadata_as_rsp(dut, clk, size=0, addr=0, next_addr=0)

    await monitor_task_metadata_req
    # assert dut.metadata_req_which_req_o.value == 2

    await FallingEdge(clk)
    await RisingEdge(clk)
    await send_metadata_as_rsp(dut, clk, size=0, addr=0, next_addr=0)

    await monitor_task_metadata_req
    # assert dut.metadata_req_which_req_o.value == 3

    await FallingEdge(clk)
    await send_metadata_as_rsp(dut, clk, size=0, addr=0, next_addr=0)

    await monitor_task_metadata_req
    # assert dut.metadata_req_which_req_o.value == 3

    await FallingEdge(clk)
    await RisingEdge(clk)
    await send_metadata_as_rsp(dut, clk, size=0, addr=0, next_addr=0)

    await FallingEdge(clk)

    for i in range(10):
        await FallingEdge(clk)

    assert True
