import cocotb
from cocotb.triggers import FallingEdge, RisingEdge
from cocotb.clock import Clock

from monitor import monitor_req_from_lsu, monitor_falafel_ready
from free_list import LinkedList
from mem_rsp import (
    send_req_to_allocate,
    send_req_to_free,
    grant_lock,
    send_load_rsp_from_mem,
    send_rsp_from_mem,
)

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
