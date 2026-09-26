package com.shangui.userhelp.ticket.service;

import com.shangui.userhelp.ticket.mapper.MockTicketMapper;
import com.shangui.userhelp.ticket.service.impl.TicketServiceImpl;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;

class TicketServiceTest {

    private final TicketService ticketService = new TicketServiceImpl(new MockTicketMapper());

    @Test
    void sameIdempotencyKeyDoesNotCreateDuplicateTicket() {
        var first = ticketService.create("u1", 123L, "商品有问题", "售后", "conv-1-ticket-1");
        var second = ticketService.create("u1", 123L, "商品有问题", "售后", "conv-1-ticket-1");

        assertSame(first, second);
        assertEquals("待处理", first.status());
    }
}
