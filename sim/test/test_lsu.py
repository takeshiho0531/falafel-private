import cocotb
from cocotb.triggers import FallingEdge, RisingEdge
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


async def req_metadata_from_core(dut, clk, which_req, size, addr, next_addr):  # noqa
    dut.req_metadata_val_i = 1
    dut.req_metadata_which_req_i = which_req
    dut.req_metadata_metadata_add_i = addr
    dut.req_metadata_metadata_size_i = size
    dut.req_metadata_metadata_next_addr_i = next_addr
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.req_metadata_val_i = 0


async def rsp_metadata_from_mem(dut, clk, data=0):  # noqa
    dut.mem_rsp_val_i = 1
    dut.mem_rsp_data_i = data
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.mem_rsp_val_i = 0


@cocotb.test()
async def test_lsu(dut):
    clk = dut.clk_i
    cocotb.start_soon(Clock(clk, CLK_PERIOD, UNITS).start())

    await reset_dut(dut, clk)
    cocotb.start(sim_time_counter(dut, clk))

    # LOCK
    for i in range(10):
        await FallingEdge(clk)

    await RisingEdge(clk)

    await req_metadata_from_core(
        dut, clk=clk, which_req=0, size=20, addr=0, next_addr=50
    )  # do not need to send so much information....???　# LOCK
    # assert dut.mem_req_val_o == 1

    await FallingEdge(clk)

    dut.mem_req_rdy_i = 1

    await rsp_metadata_from_mem(dut, clk=clk, data=0)
    for i in range(2):
        await FallingEdge(clk)

    await rsp_metadata_from_mem(dut, clk=clk, data=0)

    # assert dut.rsp_metadata_val_o == 1

    # LOAD
    for i in range(10):
        await FallingEdge(clk)

    await RisingEdge(clk)

    await req_metadata_from_core(
        dut, clk=clk, which_req=2, size=20, addr=20, next_addr=50
    )  # do not need to send so much information....???　# LOAD
    # assert dut.mem_req_val_o == 1

    await FallingEdge(clk)

    dut.mem_req_rdy_i = 1

    await rsp_metadata_from_mem(dut, clk=clk, data=10)
    for i in range(2):
        await FallingEdge(clk)
    await rsp_metadata_from_mem(dut, clk=clk, data=100)
    for i in range(2):
        await FallingEdge(clk)
    # assert dut.rsp_metadata_val_o == 1

    # UPDATE_OLD_HEADER
    for i in range(10):
        await FallingEdge(clk)

    await RisingEdge(clk)

    await req_metadata_from_core(
        dut, clk=clk, which_req=3, size=40, addr=20, next_addr=50
    )  # do not need to send so much information....???　# UPDATE_OLD_HEADER
    await FallingEdge(clk)
    dut.mem_req_rdy_i = 1
    await rsp_metadata_from_mem(dut, clk=clk, data=100)

    # INSERT
    for i in range(10):
        await FallingEdge(clk)

    await RisingEdge(clk)

    await req_metadata_from_core(
        dut, clk=clk, which_req=4, size=40, addr=20, next_addr=50
    )  # do not need to send so much information....???　# INSERT
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.mem_req_rdy_i = 1
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.mem_req_rdy_i = 1
    await rsp_metadata_from_mem(dut, clk=clk, data=100)

    # DELETE
    for i in range(10):
        await FallingEdge(clk)

    await RisingEdge(clk)

    await req_metadata_from_core(
        dut, clk=clk, which_req=5, size=40, addr=20, next_addr=50
    )  # do not need to send so much information....???　# DELETE
    await FallingEdge(clk)
    dut.mem_req_rdy_i = 1
    await rsp_metadata_from_mem(dut, clk=clk, data=100)

    assert True
