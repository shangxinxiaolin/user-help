package com.shangui.userhelp.ticket.service;

import com.shangui.userhelp.ticket.domain.Ticket;

public interface TicketService {

    Ticket create(String userId, long conversationId, String description,
                  String ticketType, String idempotencyKey);
}
