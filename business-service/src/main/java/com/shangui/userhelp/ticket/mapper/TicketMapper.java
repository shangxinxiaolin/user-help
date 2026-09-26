package com.shangui.userhelp.ticket.mapper;

import com.shangui.userhelp.ticket.domain.Ticket;

public interface TicketMapper {

    Ticket findByIdempotencyKey(String key);

    Ticket save(Ticket ticket, String idempotencyKey);
}
