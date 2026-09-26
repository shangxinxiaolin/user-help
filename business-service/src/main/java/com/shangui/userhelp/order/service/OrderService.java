package com.shangui.userhelp.order.service;

import com.shangui.userhelp.order.domain.Order;

import java.util.List;

public interface OrderService {

    Order query(String userId, String orderId);

    List<Order> list(String userId);
}
