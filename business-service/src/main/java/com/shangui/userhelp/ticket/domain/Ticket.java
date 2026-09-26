package com.shangui.userhelp.ticket.domain;

public record Ticket(String ticketNo, String userId, long conversationId, String description,
                     String ticketType, String status) {
}
