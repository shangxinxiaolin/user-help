package com.shangui.userhelp.ticket.service.impl;

import com.shangui.userhelp.common.error.BusinessException;
import com.shangui.userhelp.common.error.ErrorCode;
import com.shangui.userhelp.ticket.domain.Ticket;
import com.shangui.userhelp.ticket.mapper.TicketMapper;
import com.shangui.userhelp.ticket.service.TicketService;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class TicketServiceImpl implements TicketService {

    private final TicketMapper ticketMapper;

    public TicketServiceImpl(TicketMapper ticketMapper) {
        this.ticketMapper = ticketMapper;
    }

    @Override
    public Ticket create(String userId, long conversationId, String description,
                         String ticketType, String idempotencyKey) {
        if (userId == null || userId.isBlank() || description == null || description.isBlank()
                || ticketType == null || ticketType.isBlank() || idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST, "工单参数不完整");
        }
        Ticket existing = ticketMapper.findByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            return existing;
        }
        Ticket ticket = new Ticket("TK-" + UUID.randomUUID(), userId, conversationId,
                description, ticketType, "待处理");
        return ticketMapper.save(ticket, idempotencyKey);
    }
}
