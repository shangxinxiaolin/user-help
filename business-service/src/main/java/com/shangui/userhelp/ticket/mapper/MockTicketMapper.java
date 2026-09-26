package com.shangui.userhelp.ticket.mapper;

import com.shangui.userhelp.ticket.domain.Ticket;
import org.springframework.stereotype.Repository;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Repository
public class MockTicketMapper implements TicketMapper {

    private final Map<String, Ticket> tickets = new ConcurrentHashMap<>();

    @Override
    public Ticket findByIdempotencyKey(String key) {
        return tickets.get(key);
    }

    @Override
    public Ticket save(Ticket ticket, String idempotencyKey) {
        return tickets.computeIfAbsent(idempotencyKey, ignored -> ticket);
    }
}
