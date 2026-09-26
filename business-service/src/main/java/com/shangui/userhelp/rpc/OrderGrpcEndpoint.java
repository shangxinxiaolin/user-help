package com.shangui.userhelp.rpc;

import com.shangui.userhelp.order.domain.Order;
import com.shangui.userhelp.order.service.OrderService;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;

@GrpcService
public class OrderGrpcEndpoint extends OrderServiceGrpc.OrderServiceImplBase {

    private final OrderService orderService;

    public OrderGrpcEndpoint(OrderService orderService) {
        this.orderService = orderService;
    }

    @Override
    public void queryOrder(QueryOrderRequest request, StreamObserver<QueryOrderResponse> observer) {
        try {
            Order order = orderService.query(request.getContext().getUserId(), request.getOrderId());

            observer.onNext(QueryOrderResponse.newBuilder().setSuccess(true).setMessage("success")
                    .setOrder(toProto(order)).build());

            observer.onCompleted();

        } catch (RuntimeException exception) {
            observer.onNext(QueryOrderResponse.newBuilder().setSuccess(false)
                    .setErrorCode("BUSINESS_ERROR").setMessage(exception.getMessage()).build());
            observer.onCompleted();
        }
    }

    @Override
    public void listUserOrders(ListUserOrdersRequest request, StreamObserver<ListUserOrdersResponse> observer) {
        try {
            ListUserOrdersResponse.Builder response = ListUserOrdersResponse.newBuilder().setSuccess(true);
            for (Order order : orderService.list(request.getContext().getUserId())) {
                response.addOrders(OrderBrief.newBuilder().setOrderId(order.orderId())
                        .setProduct(order.product()).setStatus(order.status()).setAmount(order.amount()).build());
            }
            observer.onNext(response.build());
            observer.onCompleted();
        } catch (RuntimeException exception) {
            observer.onNext(ListUserOrdersResponse.newBuilder().setSuccess(false)
                    .setErrorCode("BUSINESS_ERROR").build());
            observer.onCompleted();
        }
    }

    private OrderSnapshot toProto(Order order) {
        return OrderSnapshot.newBuilder().setOrderId(order.orderId()).setStatus(order.status())
                .setAmount(order.amount()).setCreatedAt(order.createdAt()).setProduct(order.product())
                .setTrackingNo(order.trackingNo()).build();
    }
}
