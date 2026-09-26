package com.shangui.userhelp.rpc;

import com.shangui.userhelp.ticket.domain.Ticket;
import com.shangui.userhelp.ticket.service.TicketService;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;

@GrpcService
public class TicketGrpcEndpoint extends TicketServiceGrpc.TicketServiceImplBase {

    private final TicketService ticketService;

    public TicketGrpcEndpoint(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @Override
    public void createTicket(CreateTicketRequest request, StreamObserver<CreateTicketResponse> observer) {
        try {
            RequestContext context = request.getContext();
            Ticket ticket = ticketService.create(context.getUserId(), parseConversationId(context.getConversationId()),
                    request.getDescription(), request.getTicketType(), request.getIdempotencyKey());
            observer.onNext(CreateTicketResponse.newBuilder().setSuccess(true).setMessage("success")
                    .setTicketNo(ticket.ticketNo()).build());
        } catch (RuntimeException exception) {
            observer.onNext(CreateTicketResponse.newBuilder().setSuccess(false)
                    .setErrorCode("BUSINESS_ERROR").setMessage(exception.getMessage()).build());
        }
        observer.onCompleted();
    }

    private long parseConversationId(String conversationId) {
        if (conversationId == null || conversationId.isBlank()) {
            return 0L;
        }
        try {
            return Long.parseLong(conversationId);
        } catch (NumberFormatException exception) {
            return 0L;
        }
    }
}
