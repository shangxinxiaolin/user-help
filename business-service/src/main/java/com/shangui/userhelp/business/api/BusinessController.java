package com.shangui.userhelp.business.api;

import com.shangui.userhelp.aftersales.domain.ReturnInfo;
import com.shangui.userhelp.aftersales.domain.WarrantyInfo;
import com.shangui.userhelp.aftersales.service.AftersalesService;
import com.shangui.userhelp.logistics.domain.LogisticsInfo;
import com.shangui.userhelp.logistics.service.LogisticsService;
import com.shangui.userhelp.order.domain.Order;
import com.shangui.userhelp.order.service.OrderService;
import com.shangui.userhelp.refund.domain.Refund;
import com.shangui.userhelp.refund.service.RefundService;
import com.shangui.userhelp.ticket.domain.Ticket;
import com.shangui.userhelp.ticket.service.TicketService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/business")
public class BusinessController {

    private final OrderService orderService;
    private final LogisticsService logisticsService;
    private final AftersalesService aftersalesService;
    private final RefundService refundService;
    private final TicketService ticketService;

    public BusinessController(OrderService orderService, LogisticsService logisticsService,
                              AftersalesService aftersalesService, RefundService refundService,
                              TicketService ticketService) {
        this.orderService = orderService;
        this.logisticsService = logisticsService;
        this.aftersalesService = aftersalesService;
        this.refundService = refundService;
        this.ticketService = ticketService;
    }

    @GetMapping("/orders/{orderId}")
    public Order queryOrder(@RequestHeader("X-User-Id") String userId, @PathVariable String orderId) {
        return orderService.query(userId, orderId);
    }

    @GetMapping("/orders")
    public List<Order> listOrders(@RequestHeader("X-User-Id") String userId) {
        return orderService.list(userId);
    }

    @GetMapping("/logistics/{trackingNo}")
    public LogisticsInfo queryLogistics(@PathVariable String trackingNo) {
        return logisticsService.query(trackingNo);
    }

    @GetMapping("/orders/{orderId}/warranty")
    public WarrantyInfo queryWarranty(@PathVariable String orderId) {
        return aftersalesService.queryWarranty(orderId);
    }

    @GetMapping("/orders/{orderId}/return-status")
    public ReturnInfo queryReturnStatus(@PathVariable String orderId) {
        return aftersalesService.queryReturnStatus(orderId);
    }

    @PostMapping("/refunds")
    public Refund submitRefund(@RequestHeader("X-User-Id") String userId,
                               @RequestParam String orderId,
                               @RequestParam String reason,
                               @RequestHeader("Idempotency-Key") String idempotencyKey) {
        return refundService.submit(userId, orderId, reason, idempotencyKey);
    }

    @PostMapping("/tickets")
    public Ticket createTicket(@RequestHeader("X-User-Id") String userId,
                               @RequestParam long conversationId,
                               @RequestParam String description,
                               @RequestParam String ticketType,
                               @RequestHeader("Idempotency-Key") String idempotencyKey) {
        return ticketService.create(userId, conversationId, description, ticketType, idempotencyKey);
    }
}
